<template>
  <transition name="notification-slide">
    <div v-if="visible" class="notification-overlay" @click.self="hide">
      <div class="notification" :class="[type, { 'mobile': isMobile }]">
        <div class="notification-content">
          <span class="notification-icon">{{ icon }}</span>
          <span class="notification-message">{{ message }}</span>
        </div>
        <button class="notification-ok-button" @click="hide">
          {{ props.okText || 'OK' }}
        </button>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'

const props = defineProps<{
  message: string
  type?: 'success' | 'error' | 'info'
  duration?: number
  okText?: string
}>()

const visible = ref(false)
const isMobile = ref(false)
let timeoutId: number | null = null

const icon = computed(() => {
  switch (props.type) {
    case 'success': return '✓'
    case 'error': return '✗'
    default: return 'ℹ'
  }
})

const show = () => {
  visible.value = true
  
  // Don't auto hide if duration is not set
  if (props.duration && props.duration > 0) {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    timeoutId = setTimeout(() => {
      hide()
    }, props.duration) as unknown as number
  }
}

const hide = () => {
  visible.value = false
  if (timeoutId) {
    clearTimeout(timeoutId)
    timeoutId = null
  }
}

// Check if device is mobile
const checkMobile = () => {
  isMobile.value = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent) || 
                   window.innerWidth <= 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  if (timeoutId) {
    clearTimeout(timeoutId)
  }
})

// Watch for visibility changes from parent
watch(() => props.message, () => {
  if (props.message) {
    show()
  }
})

// Expose methods for parent component
defineExpose({
  show,
  hide
})
</script>

<style scoped>
.notification-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 10000;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 20px;
}

.notification {
  background: var(--notification-bg, #333);
  color: var(--notification-color, #fff);
  padding: 16px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
  font-family: monospace;
  font-size: 0.95em;
  max-width: 400px;
  width: 90%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notification.mobile {
  padding: 16px;
  font-size: 1em;
  max-width: calc(100% - 40px);
}

.notification-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.notification-icon {
  font-size: 1.2em;
  flex-shrink: 0;
}

.notification-message {
  flex: 1;
  line-height: 1.4;
}

.notification-ok-button {
  align-self: flex-end;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: inherit;
  padding: 6px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-family: monospace;
  font-size: 0.9em;
  transition: all 0.2s ease;
  outline: none;
  -webkit-tap-highlight-color: transparent;
}

.notification-ok-button:hover {
  background: rgba(255, 255, 255, 0.3);
}

.notification-ok-button:active {
  transform: scale(0.98);
}

/* Type variations */
.notification.success {
  background: var(--notification-success-bg, #4caf50);
  color: var(--notification-success-color, #fff);
}

.notification.error {
  background: var(--notification-error-bg, #f44336);
  color: var(--notification-error-color, #fff);
}

.notification.info {
  background: var(--notification-info-bg, #2196f3);
  color: var(--notification-info-color, #fff);
}

/* Slide transition */
.notification-slide-enter-active,
.notification-slide-leave-active {
  transition: all 0.3s ease;
}

.notification-slide-enter-active .notification,
.notification-slide-leave-active .notification {
  transition: all 0.3s ease;
}

.notification-slide-enter-from .notification {
  transform: translateY(-20px);
  opacity: 0;
}

.notification-slide-leave-to .notification {
  transform: translateY(-20px);
  opacity: 0;
}

/* Theme variables */
:global(.theme-light) {
  --notification-bg: #333;
  --notification-color: #fff;
  --notification-success-bg: #4caf50;
  --notification-success-color: #fff;
  --notification-error-bg: #f44336;
  --notification-error-color: #fff;
  --notification-info-bg: #2196f3;
  --notification-info-color: #fff;
}

:global(.theme-dark) {
  --notification-bg: #444;
  --notification-color: #f0f0f0;
  --notification-success-bg: #388e3c;
  --notification-success-color: #fff;
  --notification-error-bg: #d32f2f;
  --notification-error-color: #fff;
  --notification-info-bg: #1976d2;
  --notification-info-color: #fff;
}

/* Mobile specific adjustments */
@media (max-width: 768px) {
  .notification-overlay {
    align-items: center;
    padding: 20px;
  }
  
  .notification {
    max-width: 100%;
  }
}
</style> 