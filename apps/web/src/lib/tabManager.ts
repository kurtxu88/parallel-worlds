import { ref, computed } from 'vue'

// Types
interface TabInfo {
  tabId: string
  lastActivity: number
  isLeader: boolean
}

// Constants
const TAB_ACTIVITY_TIMEOUT = 5000 // 5 seconds
const TAB_CHECK_INTERVAL = 1000 // 1 second
const STORAGE_KEY = 'app_active_tab'

// State
const currentTabId = ref<string>(generateTabId())
const isActiveTab = ref(false)
const otherTabActive = ref(false)

// Generate unique tab ID
function generateTabId(): string {
  return `tab_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`
}

// Broadcast channel for cross-tab communication
let broadcastChannel: BroadcastChannel | null = null
let checkInterval: number | null = null

// Initialize tab manager
function initTabManager() {
  // Try to claim leadership immediately
  checkLeadership()
  
  // Initialize broadcast channel if supported
  if (typeof BroadcastChannel !== 'undefined') {
    broadcastChannel = new BroadcastChannel('app_tab_manager')
    
    broadcastChannel.onmessage = (event) => {
      const { type, data } = event.data
      
      switch (type) {
        case 'TAB_ACTIVE':
          handleOtherTabActive(data)
          break
        case 'TAB_CLOSING':
          handleTabClosing(data)
          break
        case 'REQUEST_LEADER':
          handleLeaderRequest()
          break
      }
    }
    
    // Request leadership
    broadcastChannel.postMessage({
      type: 'REQUEST_LEADER'
    })
  }
  
  // Start checking for leadership
  checkInterval = window.setInterval(() => {
    checkLeadership()
  }, TAB_CHECK_INTERVAL)
  
  // Also check leadership more frequently for the first few seconds
  // This helps with quick tab switching
  let quickCheckCount = 0
  const quickCheckInterval = window.setInterval(() => {
    checkLeadership()
    quickCheckCount++
    if (quickCheckCount >= 5) {
      clearInterval(quickCheckInterval)
    }
  }, 200) // Check every 200ms for the first second
  
  // Listen for storage events (fallback for browsers without BroadcastChannel)
  window.addEventListener('storage', handleStorageChange)
  
  // Handle page visibility changes
  document.addEventListener('visibilitychange', handleVisibilityChange)
  
  // Handle tab close
  window.addEventListener('beforeunload', handleBeforeUnload)
}

// Update tab activity in localStorage
function updateTabActivity() {
  const tabInfo: TabInfo = {
    tabId: currentTabId.value,
    lastActivity: Date.now(),
    isLeader: isActiveTab.value
  }
  
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tabInfo))
  } catch (e) {
    console.warn('Failed to update tab activity:', e)
  }
}

// Check if this tab should be the leader
function checkLeadership() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    
    if (!stored) {
      // No active tab, claim leadership
      claimLeadership()
      return
    }
    
    const tabInfo: TabInfo = JSON.parse(stored)
    const now = Date.now()
    
    // Check if stored tab is stale
    if (now - tabInfo.lastActivity > TAB_ACTIVITY_TIMEOUT) {
      // Previous leader is stale, claim leadership
      claimLeadership()
    } else if (tabInfo.tabId === currentTabId.value) {
      // This tab is the leader, update activity
      if (isActiveTab.value) {
        updateTabActivity()
      }
    } else {
      // Another tab is active
      if (isActiveTab.value) {
        // This tab was active but lost leadership
        isActiveTab.value = false
        otherTabActive.value = true
      }
    }
  } catch (e) {
    console.warn('Failed to check leadership:', e)
    // On error, try to claim leadership
    claimLeadership()
  }
}

// Claim leadership
function claimLeadership() {
  isActiveTab.value = true
  otherTabActive.value = false
  updateTabActivity()
  
  // Broadcast leadership claim
  if (broadcastChannel) {
    broadcastChannel.postMessage({
      type: 'TAB_ACTIVE',
      data: { tabId: currentTabId.value }
    })
  }
}

// Handle other tab becoming active
function handleOtherTabActive(data: { tabId: string }) {
  if (data.tabId !== currentTabId.value) {
    isActiveTab.value = false
    otherTabActive.value = true
  }
}

// Handle tab closing
function handleTabClosing(data: { tabId: string }) {
  if (data.tabId !== currentTabId.value) {
    // Another tab is closing, check if we should become leader
    setTimeout(() => {
      checkLeadership()
    }, 100)
  }
}

// Handle leader request
function handleLeaderRequest() {
  if (isActiveTab.value) {
    // Respond that this tab is the leader
    if (broadcastChannel) {
      broadcastChannel.postMessage({
        type: 'TAB_ACTIVE',
        data: { tabId: currentTabId.value }
      })
    }
  }
}

// Handle storage change (fallback for BroadcastChannel)
function handleStorageChange(event: StorageEvent) {
  if (event.key === STORAGE_KEY) {
    checkLeadership()
  }
}

// Handle visibility change
function handleVisibilityChange() {
  if (!document.hidden && !isActiveTab.value) {
    // Tab became visible, try to claim leadership
    checkLeadership()
  }
}

// Handle before unload
function handleBeforeUnload() {
  if (isActiveTab.value) {
    // Notify other tabs that this leader is closing
    if (broadcastChannel) {
      broadcastChannel.postMessage({
        type: 'TAB_CLOSING',
        data: { tabId: currentTabId.value }
      })
    }
    
    // Clear leadership in storage
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch (e) {
      // Ignore errors during unload
    }
  }
  
  // Cleanup
  if (broadcastChannel) {
    broadcastChannel.close()
  }
  
  if (checkInterval) {
    clearInterval(checkInterval)
  }
  
  window.removeEventListener('storage', handleStorageChange)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
}

// Export composable
export const useTabManager = () => {
  // Initialize on first use
  if (!checkInterval) {
    initTabManager()
  }
  
  return {
    isActiveTab: computed(() => isActiveTab.value),
    otherTabActive: computed(() => otherTabActive.value),
    currentTabId: computed(() => currentTabId.value),
    forceActivateTab: () => {
      // Force claim leadership immediately
      claimLeadership()
      // Update localStorage to ensure persistence
      updateTabActivity()
      // Broadcast multiple times to ensure other tabs receive it
      if (broadcastChannel) {
        for (let i = 0; i < 3; i++) {
          setTimeout(() => {
            broadcastChannel!.postMessage({
              type: 'TAB_ACTIVE',
              data: { tabId: currentTabId.value }
            })
          }, i * 100)
        }
      }
    }
  }
}