<script setup>
import { ref, watch, nextTick, onMounted, computed } from 'vue'
import { validateFen } from 'fentastic'
import MarkdownIt from 'markdown-it'
import { useChessStore } from '@/stores/useChessStore' // Import store

const chessStore = useChessStore()

const remote_server_url = import.meta.env.BASE_URL + 'backend'
const local_server_url = 'http://localhost:5000'
const starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'

// Computed for current model to send in requests
const selectedModelId = computed(() => chessStore.selectedModel)
const selectedEvaluatorModelId = computed(() => chessStore.selectedEvaluatorModel)
const availableModels = ref([])

//emits
const emit = defineEmits(['loadingChat'])

// Props
const props = defineProps({
  fen: {
    type: String,
    required: true,
  },
  depth: {
    type: Number,
    required: true,
  },
})
// Markdown
const md = new MarkdownIt({ html: true })

// Reactive state
const userInput = ref('')
const messages = ref([])
const loading = ref(false)
const toAnalyse = ref(true)
const justCopiedMsg = ref(false)
const selectedStyle = ref('default')
const analysisStyles = ref([
  { value: 'default', label: 'Commentator' }, // Always present as fallback
])

const isClipboardCopyingAvailable = ref(true)
const isLocalBackendAvailable = ref(false)
const checkingLocalBackend = ref(true)

// Computed property for server URL
const server_url = ref(remote_server_url)

// Methods

async function checkLocalBackendAvailability() {
  console.log('Checking local backend availability...')
  try {
    // Check if local backend is available by testing the health endpoint first
    const healthCheck = await fetch(local_server_url + '/health', {
      method: 'GET',
      signal: AbortSignal.timeout(500), // 500ms timeout
    })

    if (healthCheck.ok) {
      // Double-check with analysis/styles endpoint to ensure AI functionality is available
      const stylesCheck = await fetch(local_server_url + '/analysis', {
        method: 'OPTIONS',
        signal: AbortSignal.timeout(500),
      })

      if (stylesCheck.ok) {
        console.log('Local backend detected and AI endpoints available! Switching to localhost.')
        isLocalBackendAvailable.value = true
        server_url.value = local_server_url
        return
      }
    }

    console.log('Local backend not available. Using remote server.')
    isLocalBackendAvailable.value = false
    server_url.value = remote_server_url
  } catch (error) {
    console.log('Error checking local backend:', error)
    isLocalBackendAvailable.value = false
    server_url.value = remote_server_url
  } finally {
    checkingLocalBackend.value = false
  }
}

async function recheckLocalBackend() {
  checkingLocalBackend.value = true
  await checkLocalBackendAvailability()
  // Re-fetch styles from the newly selected server
  await fetchAnalysisStyles()
}

async function fetchAnalysisStyles() {
  console.log('Fetching analysis styles from server...')
  try {
    const response = await fetch(remote_server_url + '/analysis/styles')
    if (response.ok) {
      const data = await response.json()
      if (data.styles && Array.isArray(data.styles)) {
        analysisStyles.value = data.styles
        // Ensure "Commentator" (default) is always present
        const hasDefault = analysisStyles.value.some((style) => style.value === 'default')
        if (!hasDefault) {
          analysisStyles.value.unshift({ value: 'default', label: 'Commentator' })
        }
      }
    } else {
      console.warn('Failed to fetch analysis styles, using fallback')
    }
  } catch (error) {
    console.error('Error fetching analysis styles:', error)
    // Keep fallback styles if API fails
  }
}

async function sendMessageSTREAMED() {
  if (userInput.value.trim() === '') return

  const userMessage = { role: 'user', content: userInput.value }
  messages.value.push(userMessage)
  userInput.value = ''
  loading.value = true
  emit('loadingChat', true)
  scrollToBottom()

  try {
    // Capture the model ID at the time of sending
    const currentModelId = selectedModelId.value
    const currentEvaluatorId = selectedEvaluatorModelId.value
    let modelParam = currentModelId
      ? `&model=${encodeURIComponent(currentModelId)}`
      : ''

    if (currentEvaluatorId) {
      modelParam += `&evaluator_model=${encodeURIComponent(currentEvaluatorId)}`
    }

    const response = await fetch(
      server_url.value + `/response?style=${selectedStyle.value}${modelParam}&fen=${encodeURIComponent(props.fen)}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(messages.value),
      },
    )

    if (!response.ok || !response.body) {
      throw new Error('Network response was not ok')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let rawBuffer = ''

    messages.value.push({ role: 'assistant', content: '', modelId: currentModelId })

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      rawBuffer += decoder.decode(value, { stream: true })

      if (rawBuffer.includes('[START_STREAM]')) {
        const parts = rawBuffer.split('[START_STREAM]')
        const activePart = parts[1] // text after start stream

        const evalSplit = activePart.split('\n[EVALUATION]')
        const content = evalSplit[0].replace('[END_STREAM]', '')

        messages.value[messages.value.length - 1].content = content

        if (evalSplit.length > 1) {
          try {
            messages.value[messages.value.length - 1].evaluation = JSON.parse(evalSplit[1])
          } catch (e) {
            console.log("Incomplete JSON, wait for next chunk", e)
          }
        }
        scrollToBottom()
      }
    }

    // Final cleanup
  } catch (error) {
    console.error('Streaming error:', error)
    messages.value.push({ role: 'assistant', content: 'Error: unable to fetch response.' })
    scrollToBottom()
  } finally {
    loading.value = false
    emit('loadingChat', false)
    console.log(messages.value)
  }
}

async function startAnalysisSTREAMED() {
  toAnalyse.value = false
  messages.value.length = 0
  const fenToAnalyse = validateFen(props.fen.trim()).valid ? props.fen.trim() : starting_fen

  if (validateFen(fenToAnalyse).valid) {
    loading.value = true
    emit('loadingChat', true)

    try {
      // Capture the model ID at the time of analysis
      const currentModelId = selectedModelId.value
      const currentEvaluatorId = selectedEvaluatorModelId.value
      const response = await fetch(server_url.value + '/analysis', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fen: fenToAnalyse,
          depth: props.depth,
          style: selectedStyle.value,
          model: currentModelId,
          evaluator_model: currentEvaluatorId,
        }),
      })

      if (!response.ok || !response.body) {
        console.error(response.ok, response.body)
        throw new Error('Network response was not ok.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let rawBuffer = ''
      let promptProcessed = false

      messages.value.push({ role: 'assistant', content: '', modelId: currentModelId })

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        rawBuffer += decoder.decode(value, { stream: true })

        // Process prompt if present and not processed
        if (!promptProcessed && rawBuffer.includes('[PROMPT_END]')) {
          const promptEndIndex = rawBuffer.indexOf('[PROMPT_END]')
          const promptPart = rawBuffer.substring(0, promptEndIndex)
          try {
            // Find valid JSON start
            const jsonStart = promptPart.indexOf('{')
            if (jsonStart > -1) {
              const promptData = JSON.parse(promptPart.substring(jsonStart))
              const systemPrompt = promptData.prompt
              messages.value.unshift({
                role: 'system',
                content: systemPrompt,
                hidden: true,
              })
              promptProcessed = true
            }
          } catch (e) {
            console.error('Error parsing prompt:', e)
          }
        }

        if (rawBuffer.includes('[START_STREAM]')) {
          const parts = rawBuffer.split('[START_STREAM]')
          const activePart = parts[1] // text after start stream

          const evalSplit = activePart.split('\n[EVALUATION]')
          const content = evalSplit[0].replace('[END_STREAM]', '')

          messages.value[messages.value.length - 1].content = content

          if (evalSplit.length > 1) {
            try {
              messages.value[messages.value.length - 1].evaluation = JSON.parse(evalSplit[1])
            } catch (e) {
              console.log("Waiting full JSON", e)
            }
          }
          scrollToBottom()
        }
      }

      // Final cleanup
      // Content already updated in loop
    } catch (error) {
      console.error('Streaming error:', error)
      messages.value.push({ role: 'assistant', content: 'Error: unable to fetch analysis.' })
      scrollToBottom()
    } finally {
      loading.value = false
      emit('loadingChat', false)
    }
  }
}

// Watcher
watch(
  () => props.fen,
  () => {
    toAnalyse.value = true
  },
)
// Add this watcher
watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
  },
)
// Reset to analyze state when style changes
watch(
  () => selectedStyle.value,
  () => {
    if (messages.value.length > 0) {
      toAnalyse.value = true
    }
  },
)
// Custom Markdown Renderer to handle <think> tags or raw text
function renderedMarkdown(content) {
  if (!content) return ''

  // Split content by <think> tags to process markdown separately
  const thinkRegex = /<think>([\s\S]*?)(?:<\/think>|$)/gi
  const matches = []
  let match

  // Find all <think> blocks and their positions
  while ((match = thinkRegex.exec(content)) !== null) {
    matches.push({
      fullMatch: match[0],
      thinkContent: match[1],
      index: match.index
    })
  }

  if (matches.length === 0) {
    // No <think> tags, just render markdown normally
    return md.render(content)
  }

  // Process content with <think> tags
  let lastIndex = 0
  let processedParts = []

  for (const match of matches) {
    // Add markdown-rendered content before this <think> tag
    if (match.index > lastIndex) {
      const beforeThink = content.substring(lastIndex, match.index)
      processedParts.push(md.render(beforeThink))
    }

    // Add the <think> content with markdown rendered inside
    const renderedThinkContent = md.render(match.thinkContent)
    processedParts.push(
      `<details class="thinking-details" open><summary>Thinking Process</summary><div class="thinking-content">${renderedThinkContent}</div></details>`
    )

    lastIndex = match.index + match.fullMatch.length
  }

  // Add any remaining content after the last <think> tag
  if (lastIndex < content.length) {
    const afterThink = content.substring(lastIndex)
    processedParts.push(md.render(afterThink))
  }

  return processedParts.join('')
}

function scrollToBottom() {
  nextTick(() => {
    const messagesEl = document.getElementById('messages')
    if (messagesEl) {
      messagesEl.scrollTo({
        top: messagesEl.scrollHeight,
        behavior: 'smooth',
      })
    }
  })
}

// Copy text to clipboard
async function copyMessage(text) {
  try {
    await navigator.clipboard.writeText(text)
    justCopiedMsg.value = true
    setTimeout(() => {
      justCopiedMsg.value = false
    }, 1000)
  } catch (err) {
    console.error('Copying failed:', err)
  }
}

//  Regenerate assistant reply

async function regenerateMessage(index) {
  const lastUserIndex = messages.value
    .slice(0, index)
    .map((msg, i) => ({ msg, i }))
    .reverse()
    .find((item) => item.msg.role === 'user')?.i
  if (lastUserIndex === undefined) return
  const lastUserMessage = messages.value[lastUserIndex]
  userInput.value = lastUserMessage.content
  messages.value.splice(index - 1, 2)
  await sendMessageSTREAMED()
}

onMounted(async () => {
  isClipboardCopyingAvailable.value = navigator.clipboard.writeText ? true : false
  await checkLocalBackendAvailability()
  await fetchAnalysisStyles()
  // Fetch available models
  try {
    const res = await fetch(`${server_url.value}/llm/models`)
    const data = await res.json()
    availableModels.value = data.models
  } catch (e) {
    console.error('Failed to fetch models in AIChat', e)
  }
})

function getScoreClass(score) {
  if (score >= 7) return 'bg-success'
  if (score >= 5) return 'bg-warning text-dark'
  return 'bg-danger'
}
</script>

<template>
  <div class="container-fill d-flex flex-column overflow-auto p-3 me-0 rounded-4 w-100 h-100">
    <!-- Chat Messages -->
    <div id="messages" class="flex-grow-1 h-100 overflow-auto" style="scroll-behavior: smooth">
      <div v-for="(message, i) in messages" :key="i">
        <div v-if="message.role === 'user'" class="d-flex mb-1 justify-content-end">
          <div class="p-3 px-4 rounded-4 ms-5" id="usermessage">
            <div class="text-break text-start message" v-html="md.render(message.content)"></div>
          </div>
        </div>

        <div v-else-if="message.role === 'assistant'" class="p-3 pe-4 rounded-4 me-5">
          <h6 class="mb-0">AI:</h6>
          <div class="text-break text-start message" v-html="renderedMarkdown(message.content)"></div>

          <!-- Evaluation Display -->
          <div v-if="message.evaluation" class="evaluation-box mt-3 rounded"
            style="background-color: #262421; border: 1px solid #444;">
            <details>
              <summary class="d-flex justify-content-between align-items-center p-2 rounded-top cursor-pointer"
                style="background-color: #1a1916; color: #aaa23a; user-select: none;">
                <span class="fw-bold" style="font-size: 0.85rem;">
                  Evaluation by {{ message.evaluation.model_name }}
                </span>
                <span class="badge" :class="getScoreClass(message.evaluation.score)" style="font-size: 0.9em;">
                  {{ message.evaluation.score }}/10
                </span>
              </summary>
              <div class="evaluation-content p-3 border-top border-secondary">
                <p v-if="message.evaluation.reason" class="mb-0 text-white-50" style="font-size: 0.9em;">
                  {{ message.evaluation.reason }}
                </p>
              </div>
            </details>
          </div>

          <!-- Model name display -->
          <div v-if="message.modelId" class="model-name-badge mt-2">
            <small>{{availableModels.find((m) => m.id === message.modelId)?.name || message.modelId}}</small>
          </div>
          <!-- Action buttons (copy / retry) -->
          <div v-if="!loading && isClipboardCopyingAvailable" class="d-flex message-actions">
            <span v-if="!justCopiedMsg" class="material-icons-outlined p-2 fs-5" role="button" title="Copia"
              @click="copyMessage(message.content)">
              content_copy
            </span>
            <span v-else class="material-icons-outlined p-2 fs-5" role="button" title="Copiato!">
              check
            </span>
            <span class="material-icons-outlined p-2 fs-5" role="button" title="Rigenera" @click="regenerateMessage(i)">
              refresh
            </span>
          </div>
        </div>
      </div>
      <div v-if="loading" class="thinking-indicator p-3 pe-4 rounded-4 me-5">
        <div class="text-break text-start">
          <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
        </div>
      </div>
    </div>

    <!-- AI PC Status Indicator -->
    <div class="ai-pc-status text-center mb-2">
      <div v-if="checkingLocalBackend" class="d-flex justify-content-center align-items-center gap-2">
        <span class="spinner-border spinner-border-sm text-warning" role="status" aria-hidden="true"></span>
        <small class="text-warning">Checking local AI PC...</small>
      </div>
      <div v-else-if="isLocalBackendAvailable" class="d-flex justify-content-center align-items-center gap-2">
        <div class="status-indicator status-online"></div>
        <small class="text-success fw-bold">AI PC Enabled</small>
        <button class="btn btn-sm p-1 ms-2 refresh-btn" @click="recheckLocalBackend" title="Re-check local backend"
          :disabled="checkingLocalBackend">
          <span class="material-icons-outlined" style="font-size: 14px">refresh</span>
        </button>
      </div>
    </div>

    <!-- AI Content Disclaimer -->
    <div class="disclaimer-text text-center mt-2 mb-2">
      <small class="text-secondary">
        AI-generated content may contain errors or inaccuracies. Please verify important
        information.
      </small>
    </div>

    <div class="flex-shrink-0">
      <div v-if="toAnalyse" class="flex-item">
        <!-- Style Selector and Analyze Button - Horizontally Spaced -->
        <div class="d-flex justify-content-center align-items-center gap-3 mb-3">
          <div class="d-flex flex-column align-items-center">
            <label for="style-selector" class="style-label mb-1">Analysis Style</label>
            <select id="style-selector" v-model="selectedStyle" class="form-select style-selector"
              aria-label="Analysis Style">
              <option v-for="style in analysisStyles" :key="style.value" :value="style.value">
                {{ style.label }}
              </option>
            </select>
          </div>

          <button type="button" class="btn btn-sm fs-4 text-black rounded rounded-4 custom-bg-primary px-5 py-3 fw-bold"
            @click="startAnalysisSTREAMED">
            Analyze
          </button>
        </div>
      </div>
      <input v-model="userInput" v-else @keyup.enter="sendMessageSTREAMED" id="input"
        class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white custom-box" placeholder="Ask Anything!"
        autocomplete="off" />
    </div>
  </div>
</template>

<style scoped>
.message-actions {
  color: #bbb;
}

.message-actions>span {
  border-radius: 50%;
}

.message-actions>span:hover {
  background-color: #ffffff1e;
}

.custom-box {
  background-color: #2e2e2e;
  border-color: #2e2e2e !important;
  outline: none;
}

.custom-bg-primary {
  border: 2px solid #aaa23a;
}

.custom-bg-primary:hover {
  border: 2px solid #aaa23a;
  background-color: transparent;
  color: #aaa23a !important;
}

#input::placeholder {
  color: #b2b2b2;
}

#usermessage {
  background: #323232 !important;
}

.message>*:not(.thinking-details) {
  margin: 0% !important;
}

.message>.thinking-details {
  margin-top: 0 !important;
  margin-bottom: 16px !important;
}

.spinner-border,
h6 {
  color: #aaa23a;
  /* Spinner color */
}

#messages {
  overflow: auto;
  max-height: 100%;
  scrollbar-width: thin;
  scrollbar-color: #888 transparent;
}

/* width */
::-webkit-scrollbar {
  width: 10px;
}

/* Track */
::-webkit-scrollbar-track {
  background: transparent;
}

/* Handle */
::-webkit-scrollbar-thumb {
  background: #888;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
  background: #555;
}

.disclaimer-text {
  border-top: 1px solid #3a3a3a;
  padding-top: 8px;
}

.disclaimer-text small {
  font-size: 0.75rem;
  opacity: 0.8;
}

.ai-pc-status {
  border-bottom: 1px solid #3a3a3a;
  padding-bottom: 8px;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-online {
  background-color: #28a745;
  box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
  animation: pulse 2s infinite;
}

.status-offline {
  background-color: #6c757d;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
  }

  50% {
    box-shadow: 0 0 16px rgba(40, 167, 69, 0.8);
  }

  100% {
    box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
  }
}

.refresh-btn {
  background: none;
  border: none;
  color: #6c757d;
  transition: color 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
  color: #aaa23a;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.style-selector {
  background-color: #2e2e2e;
  border: 2px solid #aaa23a;
  color: #fff;
  border-radius: 8px;
  padding: 8px 12px;
  min-width: 150px;
  max-width: 200px;
  flex-shrink: 0;
}

.style-selector:focus {
  background-color: #2e2e2e;
  border-color: #aaa23a;
  color: #fff;
  box-shadow: 0 0 0 0.2rem rgba(170, 162, 58, 0.25);
}

.style-selector option {
  background-color: #2e2e2e;
  color: #fff;
}

.style-label {
  color: #aaa23a;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: center;
  margin: 0;
}

.model-name-badge {
  display: inline-block;
  background-color: #2e2e2e;
  border: 1px solid #444;
  border-radius: 12px;
  padding: 4px 10px;
  color: #aaa23a;
  font-size: 0.75rem;
  font-weight: 500;
  opacity: 0.8;
}

.cursor-pointer {
  cursor: pointer;
}

/* Hide default details marker */
.evaluation-box summary {
  list-style: none;
}
.evaluation-box summary::-webkit-details-marker {
  display: none;
}
</style>

<style>
/* Add global style for the thinking box injected via v-html */
.thinking-details {
  background-color: #262421;
  border: 1px solid #444;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 0.9em;
  margin-top: 10px;
}

.thinking-details summary {
  padding: 8px 12px;
  cursor: pointer;
  font-weight: bold;
  color: #aaa23a;
  background-color: #1a1916;
  border-top-left-radius: 8px;
  border-top-right-radius: 8px;
  user-select: none;
}

.thinking-details summary:hover {
  background-color: #2f2d2a;
}

.thinking-content {
  padding: 10px 10px 0 10px;
  color: #bbb;
  border-top: 1px solid #444;
}
</style>
