<template>
  <div v-if="lines && lines.length > 0 || loading" class="engine-lines">
    <div class="lines-header">
      <span class="header-text">Engine Analysis</span>
      <span class="depth-badge">Depth {{ depth }}</span>
    </div>
    
    <div class="lines-container">
      <!-- Loading overlay on top of content -->
      <div v-if="loading" class="loading-overlay">
        <div class="spinner"></div>
        <span class="loading-text">Analyzing...</span>
      </div>
      
      <div 
        v-for="(line, index) in displayLines" 
        :key="index"
        class="engine-line"
        :class="{ 'best-line': index === 0 }"
      >
        <div class="line-evaluation">
          <span class="line-rank">{{ index + 1 }}.</span>
          <span class="eval-score" :class="getEvaluationClass(line.evaluation)">
            {{ formatEvaluation(line.evaluation) }}
          </span>
        </div>
        <div class="line-moves">
          <span 
            v-for="(move, moveIndex) in parseMoves(line.moves)" 
            :key="moveIndex"
            class="line-move"
            :class="{ 'white-move': move.isWhite, 'black-move': !move.isWhite }"
            @click="onMoveClicked(move.san, line, moveIndex)"
          >
            <span v-if="move.moveNumber" class="move-number">{{ move.moveNumber }}.</span>
            {{ move.san }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Chess } from 'chess.js'
import { DEFAULT_SHOW_LINES } from '@/constants/evaluation.js'

const props = defineProps({
  lines: {
    type: Array,
    default: () => []
  },
  maxLines: {
    type: Number,
    default: DEFAULT_SHOW_LINES
  },
  depth: {
    type: Number,
    default: 0
  },
  currentFen: {
    type: String,
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['moveClicked'])

function onMoveClicked(move, line, moveIndex) {
  emit('moveClicked', move, line, moveIndex)
}

// Helper function to determine whose turn it is from FEN
const isWhiteToMove = computed(() => {
  if (!props.currentFen) return true
  const fenParts = props.currentFen.split(' ')
  return fenParts[1] === 'w'
})

// Display only the requested number of lines
const displayLines = computed(() => {
  if (!props.lines) return []
  return props.lines.slice(0, props.maxLines)
})

// Parse moves from the engine line format and convert UCI to SAN
function parseMoves(movesString) {
  if (!movesString || !props.currentFen) return []
  
  // Split moves and clean them
  const uciMoves = movesString.trim().split(/\s+/)
  const parsedMoves = []
  
  // Create a chess instance starting from current position
  const chess = new Chess(props.currentFen)
  
  // Determine starting move number from current FEN
  const fenParts = props.currentFen.split(' ')
  const isWhiteToMove = fenParts[1] === 'w'
  const fullMoveNumber = parseInt(fenParts[5]) || 1
  
  let currentMoveNumber = fullMoveNumber
  let isCurrentlyWhite = isWhiteToMove
  
  uciMoves.forEach((uciMove, index) => {
    // Skip move numbers that might be in the string
    if (uciMove.match(/^\d+\.+$/)) return
    
    // Clean move notation
    const cleanUciMove = uciMove.replace(/^\d+\.+/, '')
    if (!cleanUciMove) return
    
    try {
      // Convert UCI to SAN using chess.js
      const move = chess.move(cleanUciMove)
      if (move) {
        parsedMoves.push({
          san: move.san,
          uci: cleanUciMove,
          isWhite: isCurrentlyWhite,
          moveNumber: isCurrentlyWhite ? currentMoveNumber : null
        })
        
        // Update move tracking
        if (isCurrentlyWhite) {
          isCurrentlyWhite = false
        } else {
          isCurrentlyWhite = true
          currentMoveNumber++
        }
      }
    } catch (error) {
      console.warn(`Failed to parse UCI move: ${cleanUciMove}`, error)
      // If parsing fails, still show the original move
      parsedMoves.push({
        san: cleanUciMove,
        uci: cleanUciMove,
        isWhite: isCurrentlyWhite,
        moveNumber: isCurrentlyWhite ? currentMoveNumber : null
      })
      
      // Update move tracking
      if (isCurrentlyWhite) {
        isCurrentlyWhite = false
      } else {
        isCurrentlyWhite = true
        currentMoveNumber++
      }
    }
  })

  // Limit to first 6 moves for display
  return parsedMoves.slice(0, 6)
}

// Format evaluation score considering side to move
function formatEvaluation(evaluation) {
  if (evaluation === null || evaluation === undefined) return '0.0'
  
  // Determine if we need to flip the evaluation based on whose turn it was
  // The evaluation is always from the perspective of the side to move
  // We want to show it from White's perspective consistently
  let adjustedEvaluation = evaluation
  if (!isWhiteToMove.value) {
    // If it was black to move, flip the evaluation to show from white's perspective
    adjustedEvaluation = -evaluation
  }
  
  if (Math.abs(adjustedEvaluation) > 900) {
    // Mate in N moves
    const mateIn = Math.abs(adjustedEvaluation) - 1000
    const sign = adjustedEvaluation > 0 ? '+' : ''
    return `M${sign}${adjustedEvaluation > 0 ? mateIn : -mateIn}`
  }
  
  // Regular evaluation in centipawns, convert to pawns
  const pawns = adjustedEvaluation / 100
  const sign = pawns >= 0 ? '+' : ''
  return `${sign}${pawns.toFixed(1)}`
}

// Get CSS class for evaluation color considering side to move
function getEvaluationClass(evaluation) {
  if (evaluation === null || evaluation === undefined) return 'neutral'
  
  // Adjust evaluation based on whose turn it was (same logic as formatEvaluation)
  let adjustedEvaluation = evaluation
  if (!isWhiteToMove.value) {
    adjustedEvaluation = -evaluation
  }
  
  if (Math.abs(adjustedEvaluation) > 900) {
    // Mate
    return adjustedEvaluation > 0 ? 'white-winning' : 'black-winning'
  }
  
  if (adjustedEvaluation > 100) return 'white-better'
  if (adjustedEvaluation > 50) return 'white-slightly-better'
  if (adjustedEvaluation < -100) return 'black-better'
  if (adjustedEvaluation < -50) return 'black-slightly-better'
  
  return 'neutral'
}
</script>

<style scoped>
.engine-lines {
  background: rgba(42, 42, 42, 0.95);
  border: 1px solid #444;
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.lines-header {
  background: linear-gradient(135deg, #1a1a1a, #2a2a2a);
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #555;
}

.header-text {
  color: #e8e8e8;
  font-weight: 600;
  font-size: 0.9rem;
}

.depth-badge {
  background: #4a5568;
  color: #cbd5e0;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
}

.lines-container {
  position: relative; /* Allow absolute positioning of overlay */
  padding: 8px 0;
  min-height: 120px; /* Ensure consistent height */
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(42, 42, 42, 0.9); /* Semi-transparent background */
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  z-index: 10; /* Ensure it's on top */
  border-radius: 0 0 8px 8px; /* Match container border radius */
}

.spinner {
  width: 24px;
  height: 24px;
  border: 2px solid rgba(205, 210, 106, 0.3);
  border-top: 2px solid #cdd26a;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loading-text {
  color: #e8e8e8;
  font-size: 0.85rem;
  font-weight: 500;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.engine-line {
  display: flex;
  padding: 6px 12px;
  transition: background-color 0.2s ease;
  cursor: pointer;
  border-left: 3px solid transparent; /* Keeps consistent spacing with best line */
}

.engine-line:hover {
  background: rgba(255, 255, 255, 0.05);
}

.engine-line.best-line {
  background: rgba(205, 210, 106, 0.1);
  border-left: 3px solid #cdd26a;
}

.line-evaluation {
  flex-shrink: 0;
  width: 70px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.line-rank {
  color: #adb5bd;
  font-size: 0.8rem;
  font-weight: 500;
  width: 20px;
}

.eval-score {
  font-weight: 600;
  font-size: 0.85rem;
  min-width: 45px;
  text-align: center;
}

.eval-score.white-winning {
  color: #4fc3f7;
}

.eval-score.white-better {
  color: #81c784;
}

.eval-score.white-slightly-better {
  color: #aed581;
}

.eval-score.neutral {
  color: #bdbdbd;
}

.eval-score.black-slightly-better {
  color: #ffab91;
}

.eval-score.black-better {
  color: #ff8a65;
}

.eval-score.black-winning {
  color: #f48fb1;
}

.line-moves {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
  padding-left: 8px;
}

.line-move {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.2s ease;
  cursor: pointer;
  font-size: 0.85rem;
  font-family: 'Courier New', monospace;
}

.line-move:hover {
  background: rgba(205, 210, 106, 0.2);
  transform: translateY(-1px);
}

.line-move.white-move {
  background: rgba(255, 255, 255, 0.1);
  color: #f0f0f0;
}

.line-move.black-move {
  background: rgba(0, 0, 0, 0.3);
  color: #d0d0d0;
}

.move-number {
  font-weight: 600;
  color: #adb5bd;
  font-size: 0.8rem;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .line-evaluation {
    width: 60px;
  }
  
  .line-moves {
    padding-left: 4px;
  }
  
  .line-move {
    font-size: 0.8rem;
    padding: 1px 4px;
  }
}
</style>
