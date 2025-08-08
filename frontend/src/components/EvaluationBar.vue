<template>
  <div class="evaluation-container">
    <div class="evaluation-bar-wrapper" :class="{ 'disabled': !enabled }">
      <div class="evaluation-bar" :class="{ 'flipped': boardOrientation === 'black' }">
        <template v-if="enabled">
          <!-- Top section (black when white orientation, white when black orientation) -->
          <div 
            class="eval-section" 
            :class="boardOrientation !== 'white' ? 'black-section' : 'white-section'"
            :style="{ height: (boardOrientation !== 'white' ? blackPercentage : whitePercentage) + '%' }"
          >
            <div v-if="(boardOrientation !== 'white' ? blackPercentage : whitePercentage) > 15" 
                 class="eval-text" 
                 :class="boardOrientation !== 'white' ? 'black-text' : 'white-text'">
              {{ formatEvaluation() }}
            </div>
          </div>
          
          <!-- Bottom section (white when white orientation, black when black orientation) -->
          <div 
            class="eval-section" 
            :class="boardOrientation !== 'white' ? 'white-section' : 'black-section'"
            :style="{ height: (boardOrientation !== 'white' ? whitePercentage : blackPercentage) + '%' }"
          >
            <div v-if="(boardOrientation !== 'white' ? whitePercentage : blackPercentage) > 15" 
                 class="eval-text" 
                 :class="boardOrientation !== 'white' ? 'white-text' : 'black-text'">
              {{ formatEvaluation() }}
            </div>
          </div>
        </template>
        
        <template v-else>
          <!-- Disabled state - neutral position -->
          <div class="eval-section black-section" style="height: 50%"></div>
          <div class="eval-section white-section" style="height: 50%"></div>
        </template>
      </div>
      
      <!-- Center line -->
      <div class="center-line"></div>
      
      <!-- Disabled overlay -->
      <div v-if="!enabled" class="disabled-overlay">
        <span class="disabled-text">OFF</span>
      </div>
    </div>
    
    <!-- Evaluation details -->
    <div v-if="evaluation && enabled" class="evaluation-details">
      <div class="best-move">
        <span class="label">Best:</span> 
        <span class="move">{{ evaluation.move }}</span>
      </div>
      <div v-if="evaluation.winprob !== null" class="win-probability">
        Win: {{ Math.round(evaluation.winprob * 10) }}%
      </div>
    </div>
    
    <!-- Loading indicator -->
    <div v-if="loading && enabled" class="loading-indicator">
      <div class="spinner"></div>
    </div>
    
    <!-- Error display -->
    <div v-if="error && enabled" class="error-message">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  fen: {
    type: String,
    required: true
  },
  depth: {
    type: Number,
    default: 15
  },
  enabled: {
    type: Boolean,
    default: true
  },
  boardOrientation: {
    type: String,
    default: 'white' // 'white' or 'black'
  },
  barHeight: {
    type: Number,
    default: 800
  }
})

const evaluation = ref(null)
const loading = ref(false)
const error = ref(null)

// Convert evaluation score to percentage (0-100)
const evaluationPercentage = computed(() => {
  if (!evaluation.value) return 50 // Neutral position
  
  let score = 0
  
  if (evaluation.value.mate !== null) {
    // Mate situation - set to extreme values
    if (evaluation.value.mate > 0) {
      return 100 // White mate - white advantage
    } else {
      return 0 // Black mate - black advantage
    }
  } else if (evaluation.value.score !== null) {
    // Regular evaluation in centipawns
    score = evaluation.value.score
  } else if (evaluation.value.winprob !== null) {
    // Use win probability if available
    return evaluation.value.winprob * 10
  }
  
  // Convert centipawn evaluation to percentage
  // Use a sigmoid-like function to map scores to 0-100 range
  // Score of 0 = 50%, positive scores favor white, negative favor black
  const normalizedScore = Math.max(-1000, Math.min(1000, score))
  return Math.max(5, Math.min(95, 50 + (normalizedScore / 20))) // Clamp between 5-95% for visibility
})

// Always show evaluation from White's POV, regardless of board orientation
const whitePercentage = computed(() => {
  return evaluationPercentage.value
})

const blackPercentage = computed(() => 100 - whitePercentage.value)

const formatEvaluation = () => {
  if (!evaluation.value) return ''
  
  if (evaluation.value.mate !== null) {
    const mateSign = evaluation.value.mate > 0 ? '+' : ''
    return `M${mateSign}${evaluation.value.mate}`
  } else if (evaluation.value.score !== null) {
    const score = evaluation.value.score / 100 // Convert centipawns to pawns
    const sign = score >= 0 ? '+' : ''
    return `${sign}${score.toFixed(1)}`
  }
  
  return ''
}

const fetchEvaluation = async () => {
  if (!props.fen || !props.enabled) {
    evaluation.value = null
    return
  }
  
  try {
    loading.value = true
    error.value = null
    
    const response = await axios.post('http://localhost:5000/evaluation', {
      fen: props.fen,
      depth: props.depth,
      lines: 1 // Always use 1 line for the evaluation bar
    })
    console.log('Evaluation:', response)
    evaluation.value = response.data.evaluation
  } catch (err) {
    console.error('Error fetching evaluation:', err)
    error.value = 'Failed to get evaluation'
    evaluation.value = null
  } finally {
    loading.value = false
  }
}

// Watch for FEN changes and fetch new evaluation
watch(() => props.fen, fetchEvaluation, { immediate: true })
watch(() => props.depth, fetchEvaluation)
watch(() => props.enabled, fetchEvaluation)
watch(() => props.boardOrientation, () => {
  // No need to refetch, just update the display
})
</script>

<style scoped>
.evaluation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 5px;
  height: 100%;
}

.evaluation-bar-wrapper {
  position: relative;
  width: 40px;
  border: 2px solid #444;
  border-radius: 4px;
  overflow: hidden;
  background-color: #222;
  flex: 1;
}

.evaluation-bar-wrapper.disabled {
  opacity: 0.5;
}

.disabled-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
}

.disabled-text {
  color: #666;
  font-size: 10px;
  font-weight: bold;
  writing-mode: vertical-lr;
  text-orientation: mixed;
}

.evaluation-bar {
  display: flex;
  flex-direction: column-reverse;
  width: 100%;
  height: 100%;
  position: relative;
}

.eval-section {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: height 0.3s ease;
  position: relative;
}

.white-section {
  background: linear-gradient(to top, #f0f0f0, #d0d0d0);
}

.black-section {
  background: linear-gradient(to bottom, #1a1a1a, #333);
}

.eval-text {
  font-size: 10px;
  font-weight: bold;
  writing-mode: vertical-lr;
  text-orientation: mixed;
  transform: rotate(180deg);
}

.white-text {
  color: #000;
}

.black-text {
  color: #fff;
}

.center-line {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 2px;
  background-color: #666;
  transform: translateY(-50%);
  z-index: 10;
}

.evaluation-details {
  text-align: center;
  font-size: 12px;
  color: #f2f2f2;
}

.best-move {
  margin-bottom: 5px;
}

.label {
  color: #aaa;
}

.move {
  font-weight: bold;
  color: #cdd26a;
}

.win-probability {
  color: #bbb;
  font-size: 11px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 30px;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #444;
  border-top: 2px solid #cdd26a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-message {
  color: #ff6b6b;
  font-size: 11px;
  text-align: center;
}
</style>
