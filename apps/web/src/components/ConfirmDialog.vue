<template>
  <transition name="modal-fade">
    <div v-if="visible" class="modal-overlay" @click.self="handleCancel">
      <div class="modal-container" :class="{ 'mobile': isMobile }">
        <div class="modal-header">
          <h3>{{ title }}</h3>
        </div>
        <div class="modal-body">
          <p>{{ message }}</p>
          <p v-if="subtitle" class="subtitle">"{{ subtitle }}"</p>
        </div>
        <div class="modal-footer">
          <button 
            class="modal-button cancel-button" 
            @click="handleCancel"
            @touchstart.prevent="handleCancel"
          >
            {{ cancelText }}
          </button>
          <button 
            class="modal-button confirm-button" 
            @click="handleConfirm"
            @touchstart.prevent="handleConfirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  title: string
  message: string
  subtitle?: string
  confirmText?: string
  cancelText?: string
}>()

const emit = defineEmits(['confirm', 'cancel'])

const visible = ref(false)
const isMobile = ref(false)

const confirmText = computed(() => props.confirmText || 'Confirm')
const cancelText = computed(() => props.cancelText || 'Cancel')

const handleConfirm = () => {
  visible.value = false
  emit('confirm')
}

const handleCancel = () => {
  visible.value = false
  emit('cancel')
}

const show = () => {
  visible.value = true
  // Prevent body scroll on mobile when modal is open
  if (isMobile.value) {
    document.body.style.overflow = 'hidden'
  }
}

const hide = () => {
  visible.value = false
  // Restore body scroll
  document.body.style.overflow = ''
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
  // Ensure body scroll is restored
  document.body.style.overflow = ''
})

// Expose methods for parent component
defineExpose({
  show,
  hide
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.modal-container {
  background: var(--modal-bg, #fff);
  border-radius: 8px;
  box-shadow: 0 2px 20px rgba(0, 0, 0, 0.2);
  max-width: 400px;
  width: 100%;
  font-family: monospace;
  overflow: hidden;
}

.modal-container.mobile {
  max-width: 90%;
  margin: 0 auto;
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid var(--modal-border, #eee);
}

.modal-header h3 {
  margin: 0;
  font-size: 1.2em;
  font-weight: normal;
  color: var(--modal-title-color, #333);
}

.modal-body {
  padding: 20px;
  min-height: 60px;
}

.modal-body p {
  margin: 0 0 10px 0;
  color: var(--modal-text-color, #666);
  line-height: 1.5;
}

.modal-body .subtitle {
  font-style: italic;
  color: var(--modal-subtitle-color, #888);
  margin-top: 10px;
}

.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid var(--modal-border, #eee);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.modal-button {
  padding: 8px 20px;
  border: 1px solid var(--modal-button-border, #ddd);
  background: var(--modal-button-bg, #fff);
  color: var(--modal-button-color, #333);
  font-family: monospace;
  font-size: 0.95em;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s ease;
  -webkit-tap-highlight-color: transparent;
  touch-action: manipulation;
}

.modal-button:hover {
  background: var(--modal-button-hover-bg, #f5f5f5);
}

.confirm-button {
  background: var(--modal-confirm-bg, #000);
  color: var(--modal-confirm-color, #fff);
  border-color: var(--modal-confirm-border, #000);
}

.confirm-button:hover {
  background: var(--modal-confirm-hover-bg, #333);
}

.cancel-button:active,
.confirm-button:active {
  transform: scale(0.98);
}

/* Mobile specific styles */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px;
  }

  .modal-container {
    max-width: 95%;
  }

  .modal-button {
    padding: 12px 24px;
    font-size: 1em;
  }
}

/* Modal fade transition */
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

/* Theme variables */
:global(.theme-light) {
  --modal-bg: #fff;
  --modal-border: #eee;
  --modal-title-color: #333;
  --modal-text-color: #666;
  --modal-subtitle-color: #888;
  --modal-button-border: #ddd;
  --modal-button-bg: #fff;
  --modal-button-color: #333;
  --modal-button-hover-bg: #f5f5f5;
  --modal-confirm-bg: #000;
  --modal-confirm-color: #fff;
  --modal-confirm-border: #000;
  --modal-confirm-hover-bg: #333;
}

:global(.theme-dark) {
  --modal-bg: #1a1a1a;
  --modal-border: #333;
  --modal-title-color: #f0f0f0;
  --modal-text-color: #ccc;
  --modal-subtitle-color: #999;
  --modal-button-border: #444;
  --modal-button-bg: #2a2a2a;
  --modal-button-color: #f0f0f0;
  --modal-button-hover-bg: #333;
  --modal-confirm-bg: #f0f0f0;
  --modal-confirm-color: #1a1a1a;
  --modal-confirm-border: #f0f0f0;
  --modal-confirm-hover-bg: #ddd;
}
</style> 