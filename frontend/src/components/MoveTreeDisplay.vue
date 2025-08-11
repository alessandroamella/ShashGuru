<template>
  <div class="move-tree-display">
    

    <!-- Display moves in traditional chess notation format with inline variations -->
    <div v-if="props.node" class="moves-container">
      <div v-for="(moveItem, index) in displayItems" :key="moveItem.id || index" 
           :class="['move-item', { 'variation-item': moveItem.isVariation }]">
        
        <!-- Main move row -->
        <div v-if="moveItem.type === 'move-pair'" class="move-row">
          <!-- Move number -->
          <span class="move-number">{{ moveItem.moveNumber }}.</span>
          
          <!-- White move -->
          <span 
            v-if="moveItem.whiteMove"
            class="move-text white-move"
            :class="{ 
              'current-move': isSelectedMove(moveItem.whiteMove),
              'main-line': isMainLineMove(moveItem.whiteMove),
              'variation': !isMainLineMove(moveItem.whiteMove)
            }"
            @click="$emit('nodeClicked', moveItem.whiteMove)"
            @contextmenu.prevent="showContextMenu($event, moveItem.whiteMove)"
          >
            <span class="move-icon" v-if="getShashinIcon(moveItem.whiteMove) || getMoveEvaluationIcon(moveItem.whiteMove)">
              <span v-if="getShashinIcon(moveItem.whiteMove)" class="shashin-part">{{ getShashinIcon(moveItem.whiteMove) }}</span>
              <span v-if="getMoveEvaluationIcon(moveItem.whiteMove)" class="evaluation-part">{{ getMoveEvaluationIcon(moveItem.whiteMove) }}</span>
              <span v-if="!moveItem.whiteMove.shashinType && moveItem.whiteMove.evaluation" 
                    class="auto-indicator" title="Auto-detected from evaluation">•</span>
            </span>
            {{ moveItem.whiteMove.move }}
          </span>
          <span v-else class="move-text empty">...</span>
          
          <!-- Black move -->
          <span 
            v-if="moveItem.blackMove"
            class="move-text black-move"
            :class="{ 
              'current-move': isSelectedMove(moveItem.blackMove),
              'main-line': isMainLineMove(moveItem.blackMove),
              'variation': !isMainLineMove(moveItem.blackMove)
            }"
            @click="$emit('nodeClicked', moveItem.blackMove)"
            @contextmenu.prevent="showContextMenu($event, moveItem.blackMove)"
          >
            <span class="move-icon" v-if="getShashinIcon(moveItem.blackMove) || getMoveEvaluationIcon(moveItem.blackMove)">
              <span v-if="getShashinIcon(moveItem.blackMove)" class="shashin-part">{{ getShashinIcon(moveItem.blackMove) }}</span>
              <span v-if="getMoveEvaluationIcon(moveItem.blackMove)" class="evaluation-part">{{ getMoveEvaluationIcon(moveItem.blackMove) }}</span>
              <span v-if="!moveItem.blackMove.shashinType && moveItem.blackMove.evaluation" 
                    class="auto-indicator" title="Auto-detected from evaluation">•</span>
            </span>
            {{ moveItem.blackMove.move }}
          </span>
          <span v-else class="move-text empty">...</span>
        </div>

        <!-- Variation -->
        <div v-else-if="moveItem.type === 'variation'" class="variation-item">
          <div class="variation-line">
            <!-- <span class="variation-marker">(</span> -->
            <MoveTreeDisplay 
              :node="moveItem.variation"
              :currentNode="currentNode"
              :selectedPath="selectedPath"
              :level="level + 1"
              :isAnalysisMode="isAnalysisMode"
              @nodeClicked="$emit('nodeClicked', $event)"
              @addMove="$emit('addMove', $event)"
              @setShashinType="$emit('setShashinType', $event)"
              @setMoveEvaluation="$emit('setMoveEvaluation', $event)"
              @promoteVariation="$emit('promoteVariation', $event)"
              @deleteMove="$emit('deleteMove', $event)"
            />
            <!-- <span class="variation-marker">)</span> -->
          </div>
        </div>
      </div>
    </div>

    <!-- Analysis input for adding moves -->
    <div v-if="isCurrentNodeInTree && isAnalysisMode" class="analysis-input mt-2">
      <div class="input-group input-group-sm">
        <input 
          v-model="newMove" 
          @keyup.enter="handleAddMove"
          @keyup.esc="newMove = ''"
          class="form-control form-control-sm"
          placeholder="Add move (e.g., Nf3, e4)"
          ref="moveInput"
        />
        <button class="btn btn-outline-success btn-sm" @click="handleAddMove">
          <i class="material-icons" style="font-size: 16px;">add</i>
        </button>
      </div>
    </div>

    <!-- Context Menu -->
    <div 
      v-if="showMenu" 
      ref="contextMenu"
      class="context-menu"
      :style="{ top: menuPosition.y + 'px', left: menuPosition.x + 'px' }"
      @click.stop
    >
      <div class="context-menu-header">Move Annotations</div>
      
      <!-- Promotion section (only show for variations) -->
      <div v-if="canPromoteToMainLine" class="context-menu-section">
        <div class="context-menu-item promotion-item" @click="promoteToMainLine">
          <span class="promotion-icon">⬆️</span> Promote to Main Line
        </div>
      </div>

      <!-- Delete section (only show for moves that can be deleted) -->
      <div v-if="canDeleteMove" class="context-menu-section">
        <div class="context-menu-item delete-item" @click="deleteMove">
          <span class="delete-icon">🗑️</span> Delete Move
        </div>
      </div>
      
      <!-- Move Evaluation section -->
      <div class="context-menu-section">
        <div class="context-menu-section-title" @click="toggleSection('moveEvaluation')">
          <span class="section-toggle-icon" :class="{ 'expanded': !sectionCollapsed.moveEvaluation }">▶</span>
          Move Evaluation
        </div>
        <div v-show="!sectionCollapsed.moveEvaluation" class="section-content">
          <div class="context-menu-item" @click="setMoveEvaluation('brilliant')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('brilliant') }}</span> Brilliant
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('great')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('great') }}</span> Great
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('best')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('best') }}</span> Best
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('excellent')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('excellent') }}</span> Excellent
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('good')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('good') }}</span> Good
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('book')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('book') }}</span> Book Move
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('inaccuracy')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('inaccuracy') }}</span> Inaccuracy
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('mistake')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('mistake') }}</span> Mistake
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('blunder')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('blunder') }}</span> Blunder
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation('missed-win')">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon('missed-win') }}</span> Missed Win
          </div>
          <div class="context-menu-item" @click="setMoveEvaluation(null)">
            <span class="move-eval-icon">{{ getMoveEvaluationIcon(null) }}</span> Clear Evaluation
          </div>
        </div>
      </div>

      <!-- Shashin Position Type section -->
      <div class="context-menu-section">
        <div class="context-menu-section-title" @click="toggleSection('shashinType')">
          <span class="section-toggle-icon" :class="{ 'expanded': !sectionCollapsed.shashinType }">▶</span>
          Shashin Position Type
        </div>
        <div v-show="!sectionCollapsed.shashinType" class="section-content">
        
        <!-- Tal (Attack) positions -->
        <div class="context-menu-subsection">
          <div class="context-menu-subsection-title">Tal (Attack)</div>
          <div class="context-menu-item" @click="setShashinType('high-tal')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'high-tal' }) }}</span> High Tal
          </div>
          <div class="context-menu-item" @click="setShashinType('high-middle-tal')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'high-middle-tal' }) }}</span> High-Middle Tal
          </div>
          <div class="context-menu-item" @click="setShashinType('middle-tal')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'middle-tal' }) }}</span> Middle Tal
          </div>
          <div class="context-menu-item" @click="setShashinType('middle-low-tal')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'middle-low-tal' }) }}</span> Middle-Low Tal
          </div>
          <div class="context-menu-item" @click="setShashinType('low-tal')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'low-tal' }) }}</span> Low Tal
          </div>
        </div>

        <!-- Capablanca (Strategic) positions -->
        <div class="context-menu-subsection">
          <div class="context-menu-subsection-title">Capablanca (Strategic)</div>
          <div class="context-menu-item" @click="setShashinType('capablanca')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'capablanca' }) }}</span> Capablanca
          </div>
        </div>

        <!-- Petrosian (Defense) positions -->
        <div class="context-menu-subsection">
          <div class="context-menu-subsection-title">Petrosian (Defense)</div>
          <div class="context-menu-item" @click="setShashinType('high-petrosian')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'high-petrosian' }) }}</span> High Petrosian
          </div>
          <div class="context-menu-item" @click="setShashinType('high-middle-petrosian')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'high-middle-petrosian' }) }}</span> High-Middle Petrosian
          </div>
          <div class="context-menu-item" @click="setShashinType('middle-petrosian')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'middle-petrosian' }) }}</span> Middle Petrosian
          </div>
          <div class="context-menu-item" @click="setShashinType('middle-low-petrosian')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'middle-low-petrosian' }) }}</span> Middle-Low Petrosian
          </div>
          <div class="context-menu-item" @click="setShashinType('low-petrosian')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'low-petrosian' }) }}</span> Low Petrosian
          </div>
        </div>

        <!-- Chaos positions -->
        <div class="context-menu-subsection">
          <div class="context-menu-subsection-title">Chaos</div>
          <div class="context-menu-item" @click="setShashinType('chaos-all')">
            <span class="shashin-icon">{{ getShashinIcon({ shashinType: 'chaos-all' }) }}</span> Total Chaos
          </div>
        </div>

        <!-- Clear option -->
        <div class="context-menu-subsection">
          <div class="context-menu-item" @click="setShashinType(null)">
            <span class="shashin-icon">❌</span> Clear Shashin Type
          </div>
        </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue';
import EngineLines from './EngineLines.vue';

const props = defineProps({
  node: {
    type: Object,
    required: true
  },
  currentNode: {
    type: Object,
    required: true
  },
  selectedPath: {
    type: Array,
    default: () => []
  },
  level: {
    type: Number,
    default: 0
  },
  isAnalysisMode: {
    type: Boolean,
    default: false
  },
  engineEvaluation: {
    type: Object,
    default: () => ({
      bestMove: null,
      evaluation: null,
      depth: 0,
      lines: []
    })
  },
  isEvaluationLoading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['nodeClicked', 'addMove', 'setShashinType', 'setMoveEvaluation', 'promoteVariation', 'deleteMove']);

const newMove = ref('');
const moveInput = ref(null);
const showMenu = ref(false);
const menuPosition = ref({ x: 0, y: 0 });
const selectedNode = ref(null);
const contextMenu = ref(null);

// Section collapse states
const sectionCollapsed = ref({
  moveEvaluation: true,
  shashinType: true
});

// Create display items that include both moves and variations in proper order
const displayItems = computed(() => {
  if (!props.node) return [];
  
  const items = [];
  const startingMoveIndex = calculateStartingMoveIndex(props.node);
  buildDisplayItems(props.node, items, startingMoveIndex);
  return items;
});

// Check if current node is in this tree
const isCurrentNodeInTree = computed(() => {
  if (!props.currentNode || !props.node) return false;
  return isNodeInTree(props.currentNode, props.node);
});

function calculateStartingMoveIndex(node) {
  // If this is the root node or has no parent, start from 0
  if (!node || !node.parent) return 0;
  
  // Use the FEN string to determine whose turn it is
  // FEN format: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
  // The active color is the second field (w = white, b = black)
  const parentFen = node.parent.fen;
  if (!parentFen) return 0;
  
  const fenParts = parentFen.split(' ');
  if (fenParts.length < 6) return 0;
  
  const activeColor = fenParts[1]; // 'w' for white, 'b' for black
  const fullMoveNumber = parseInt(fenParts[5]) || 1;
  
  // Calculate the move index based on the position
  // White's first move is index 0, black's first move is index 1, etc.
  if (activeColor === 'w') {
    return (fullMoveNumber - 1) * 2;
  } else {
    return (fullMoveNumber - 1) * 2 + 1;
  }
}

function buildDisplayItems(startNode, items, moveIndex) {
  let current = startNode;
  let currentMoveIndex = moveIndex;
  
  // Skip the root node if it has no move but has children
  if (!current.move && current.mainLine) {
    current = current.mainLine;
  } else if (!current.move && current.children.length > 0) {
    // Root node with no move but has children - start with first child
    current = current.children[0];
  }
  
  while (current && current.move) {
    const isWhiteMove = currentMoveIndex % 2 === 0;
    const moveNumber = Math.floor(currentMoveIndex / 2) + 1;
    
    if (isWhiteMove) {
      // Start a new move pair with white move
      const blackMove = current.mainLine;
      const movePair = {
        type: 'move-pair',
        id: `pair-${moveNumber}`,
        moveNumber,
        whiteMove: current,
        blackMove: blackMove
      };
      items.push(movePair);
      
      // Add variations for white move
      const whiteVariations = current.children.filter(child => child !== current.mainLine);
      whiteVariations.forEach(variation => {
        items.push({
          type: 'variation',
          id: `var-${variation.id}`,
          variation: variation,
          isVariation: true
        });
      });
      
      // Add variations for black move if it exists
      if (blackMove) {
        const blackVariations = blackMove.children.filter(child => child !== blackMove.mainLine);
        blackVariations.forEach(variation => {
          items.push({
            type: 'variation',
            id: `var-${variation.id}`,
            variation: variation,
            isVariation: true
          });
        });
        
        // Move to next after black move
        current = blackMove.mainLine;
        currentMoveIndex += 2;
      } else {
        // No black move, just increment by 1
        current = null;
        currentMoveIndex += 1;
      }
    } else {
      // This is a black move starting a variation
      const movePair = {
        type: 'move-pair',
        id: `pair-${moveNumber}`,
        moveNumber,
        whiteMove: null,
        blackMove: current
      };
      items.push(movePair);
      
      // Add variations for this black move
      const variations = current.children.filter(child => child !== current.mainLine);
      variations.forEach(variation => {
        items.push({
          type: 'variation',
          id: `var-${variation.id}`,
          variation: variation,
          isVariation: true
        });
      });
      
      current = current.mainLine;
      currentMoveIndex += 1;
    }
  }
}

function getMainLineMoves(startNode) {
  const moves = [];
  let current = startNode;
  
  // Skip the root node if it has no move
  if (!current.move && current.mainLine) {
    current = current.mainLine;
  }
  
  while (current && current.move) {
    moves.push(current);
    current = current.mainLine;
  }
  
  return moves;
}

function isNodeInTree(nodeToFind, treeRoot) {
  if (!nodeToFind || !treeRoot) return false;
  if (nodeToFind.id === treeRoot.id) return true;
  
  if (treeRoot.children) {
    for (const child of treeRoot.children) {
      if (isNodeInTree(nodeToFind, child)) {
        return true;
      }
    }
  }
  
  return false;
}

function isSelectedMove(moveNode) {
  return props.currentNode && moveNode && props.currentNode.id === moveNode.id;
}

function isMainLineMove(moveNode) {
  if (!moveNode || !moveNode.parent) return true;
  return moveNode.parent.mainLine === moveNode;
}

async function handleAddMove() {
  if (newMove.value.trim()) {
    emit('addMove', newMove.value.trim());
    newMove.value = '';
  }
}


function showContextMenu(event, node) {
  selectedNode.value = node;
  showMenu.value = true;
  
  // Reset section collapsed states when opening menu
  sectionCollapsed.value = {
    moveEvaluation: true,
    shashinType: true
  };
  
  // Position the context menu
  const rect = event.target.getBoundingClientRect();
  menuPosition.value = {
    x: event.clientX,
    y: event.clientY
  };
  
  // Ensure menu stays within viewport
  nextTick(() => {
    if (contextMenu.value) {
      const menuRect = contextMenu.value.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      
      if (menuPosition.value.x + menuRect.width > viewportWidth) {
        menuPosition.value.x = viewportWidth - menuRect.width - 10;
      }
      
      if (menuPosition.value.y + menuRect.height > viewportHeight) {
        menuPosition.value.y = viewportHeight - menuRect.height - 10;
      }
    }
  });
}

function setShashinType(type) {
  if (selectedNode.value) {
    emit('setShashinType', { node: selectedNode.value, type });
  }
  hideContextMenu();
}

function setMoveEvaluation(type) {
  if (selectedNode.value) {
    emit('setMoveEvaluation', { node: selectedNode.value, type });
  }
  hideContextMenu();
}

function toggleSection(sectionName) {
  sectionCollapsed.value[sectionName] = !sectionCollapsed.value[sectionName];
}

function hideContextMenu() {
  showMenu.value = false;
  selectedNode.value = null;
}

function getShashinIcon(node) {
  if (!node) return '';

  const shashinIcons = {
      'high-tal': '⬆️⚔️',
      'high-middle-tal': '⚔️',
      'middle-tal': '⚔️',
      'middle-low-tal': '⬇️⚔️',
      'low-tal': '⚔️',
      'capablanca': '⚖️',
      'high-petrosian': '⬆️🛡️',
      'high-middle-petrosian': '⬆️🟰🛡️',
      'middle-petrosian': '🟰🛡️',
      'middle-low-petrosian': '🟰⬇️🛡️',
      'low-petrosian': '⬇️🛡️',
      'chaos-all': '🌀'
    };
  
  // If manually set, use that
  if (node.shashinType) {
    return shashinIcons[node.shashinType] || '';
  }
  
  // Auto-detect from evaluation if available
  if (node.evaluation) {
    const autoType = getAutoShashinType(node.evaluation);
    if (autoType) {
      return shashinIcons[autoType] || '';
    }
  }
  
  return '';
}

function getAutoShashinType(evaluation) {
  if (!evaluation) return null;
  // TODO: Implement auto-detection logic
  return null; // Placeholder for now
}

function getMoveEvaluationIcon(node) {
  if (!node || !node.moveEvaluation) return '';

  const evaluationIcons = {
    'brilliant': '✨',
    'great': '❗',
    'best': '✓',
    'excellent': '⚡',
    'good': '✓',
    'book': '📖',
    'inaccuracy': '⁈',
    'mistake': '❓',
    'blunder': '❌',
    'missed-win': '💔'
  };

  return evaluationIcons[node.moveEvaluation] || '';
}

// Check if the selected node can be promoted to main line
const canPromoteToMainLine = computed(() => {
  if (!selectedNode.value || !selectedNode.value.parent) return false;
  
  // Can only promote if this node is not already the main line
  const isCurrentlyMainLine = selectedNode.value.parent.mainLine === selectedNode.value;
  
  // Also check if this node is part of the main line path from root
  const isOnMainLinePath = isNodeOnMainLinePath(selectedNode.value);
  
  // Can promote if it's either not the direct main line OR not on the main line path
  const canPromote = !isCurrentlyMainLine || !isOnMainLinePath;
  
  return canPromote;
});

// Check if a node is on the main line path from root to end
function isNodeOnMainLinePath(node) {
  if (!node || !node.parent) return false;
  
  // Traverse up to find the root
  let current = node;
  while (current.parent) {
    // If at any point this node is not the main line of its parent,
    // then it's not on the main line path
    if (current.parent.mainLine !== current) {
      return false;
    }
    current = current.parent;
  }
  
  return true;
}

function promoteToMainLine() {
  if (selectedNode.value && canPromoteToMainLine.value) {
    emit('promoteVariation', selectedNode.value);
  }
  hideContextMenu();
}

// Check if the selected node can be deleted (not the root node)
const canDeleteMove = computed(() => {
  if (!selectedNode.value) return false;
  
  // Can't delete the root node (node with no move)
  return !!selectedNode.value.move;
});

function deleteMove() {
  if (selectedNode.value && canDeleteMove.value) {
    emit('deleteMove', selectedNode.value);
  }
  hideContextMenu();
}

// Click outside to close context menu
function handleClickOutside(event) {
  if (showMenu.value && contextMenu.value && !contextMenu.value.contains(event.target)) {
    hideContextMenu();
  }
}

// Add event listener for clicking outside
onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

// Focus input when analysis mode is enabled and this node is current
watch(() => [isCurrentNodeInTree.value, props.isAnalysisMode], async ([isInTree, analysisMode]) => {
  if (isInTree && analysisMode) {
    await nextTick();
    if (moveInput.value) {
      moveInput.value.focus();
    }
  }
}, { immediate: true });
</script>

<style scoped>
.move-tree-display {
  width: 100%;
  font-family: 'Courier New', monospace;
  line-height: 1.4;
}

.moves-container {
  width: 100%;
}

.move-item {
  margin-bottom: 0.1rem;
}

.move-item.variation-item {
  margin-left: 1.5rem;
  margin-top: 0.2rem;
  margin-bottom: 0.3rem;
}

.move-row {
  display: flex;
  align-items: center;
  line-height: 1.3;
}

.move-number {
  width: 1.4rem;
  text-align: right;
  margin-right: 0.35rem;
  font-weight: bold;
  color: #adb5bd;
  flex-shrink: 0;
  font-size: 0.85em;
}

.move-text {
  cursor: pointer;
  padding: 0.07rem 0.28rem;
  border-radius: 3px;
  transition: all 0.2s ease;
  min-width: 2.1rem;
  text-align: center;
  margin-right: 0.35rem;
  flex-shrink: 0;
  font-size: 0.85em;
  position: relative;
}

.move-text .move-icon {
  font-size: 0.7em;
  margin-right: 0.3rem;
  opacity: 0.8;
  position: relative;
  display: inline-block;
  line-height: 1;
  white-space: nowrap;
}

.move-text .move-icon .shashin-part {
  margin-right: 0.2rem;
}

.move-text .move-icon .evaluation-part {
  margin-left: 0.1rem;
}

.move-text .move-icon .auto-indicator {
  position: absolute;
  top: -2px;
  right: -4px;
  font-size: 0.6em;
  color: #17a2b8;
  opacity: 0.7;
}

.move-text:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.move-text.current-move {
  background-color: #cdd26a;
  color: black;
  font-weight: bold;
}

.move-text.main-line {
  color: #fff;
  font-weight: 500;
}

.move-text.variation {
  color: #adb5bd;
  font-style: italic;
}

.move-text.empty {
  color: transparent;
  cursor: default;
}

.move-text.empty:hover {
  background-color: transparent;
}

.white-move {
  background-color: rgba(255, 255, 255, 0.05);
}

.black-move {
  background-color: rgba(0, 0, 0, 0.2);
}

.variation-item {
  margin-left: 1.4rem;
}

.variation-line {
  display: flex;
  align-items: flex-start;
  flex-wrap: wrap;
  margin: 0.2rem 0;
  padding: 0.15rem 0.5rem;
  background-color: rgba(255, 255, 255, 0.02);
  border-left: 3px solid #444;
  border-radius: 0 4px 4px 0;
  font-size: 1em; /* Ensure consistent font size */
}

.variation-marker {
  color: #6c757d;
  font-weight: bold;
  margin: 0 0.25rem;
  flex-shrink: 0;
  font-size: 0.85em; /* Match move text size */
}

.variation-start {
  color: #adb5bd;
  font-weight: 500;
  margin-right: 0.5rem;
  flex-shrink: 0;
  font-size: 0.85em; /* Match move text size */
}

.analysis-input {
  margin-top: 0.75rem;
  max-width: 250px;
}

.analysis-input .form-control {
  font-size: 0.875rem;
  background-color: rgba(255, 255, 255, 0.1);
  border: 1px solid #444;
  color: #fff;
}

.analysis-input .form-control:focus {
  background-color: rgba(255, 255, 255, 0.15);
  border-color: #cdd26a;
  box-shadow: 0 0 0 0.2rem rgba(205, 210, 106, 0.25);
}

.analysis-input .btn {
  padding: 0.25rem 0.5rem;
}

/* Nested variations get deeper indentation but maintain font size */
.variation-item .move-tree-display {
  margin-left: 0;
  font-size: 1em; /* Prevent font size inheritance */
}

.variation-item .variation-item {
  margin-left: 1rem;
}

/* Context Menu Styles */
.context-menu {
  position: fixed;
  background: #2d3748;
  border: 1px solid #4a5568;
  border-radius: 8px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  min-width: 220px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.context-menu-header {
  padding: 0.75rem 1rem;
  background: #1a202c;
  color: #e2e8f0;
  font-weight: 600;
  font-size: 0.875rem;
  border-bottom: 1px solid #4a5568;
  text-align: center;
}

.context-menu-section {
  border-bottom: 1px solid #4a5568;
}

.context-menu-section:last-child {
  border-bottom: none;
}

.context-menu-section-title {
  padding: 0.5rem 1rem;
  background: #374151;
  color: #d1d5db;
  font-weight: 500;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  user-select: none;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: background-color 0.2s ease;
}

.context-menu-section-title:hover {
  background: #4a5568;
}

.section-toggle-icon {
  font-size: 0.6rem;
  transition: transform 0.2s ease;
  transform: rotate(0deg);
  color: #9ca3af;
}

.section-toggle-icon.expanded {
  transform: rotate(90deg);
}

.section-content {
  animation: slideDown 0.2s ease;
}

.context-menu-subsection {
  border-top: 1px solid #4a5568;
}

.context-menu-subsection:first-child {
  border-top: none;
}

.context-menu-subsection-title {
  padding: 0.4rem 1rem;
  background: #4a5568;
  color: #cbd5e0;
  font-weight: 500;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.context-menu-item {
  padding: 0.5rem 1rem;
  cursor: pointer;
  color: #e2e8f0;
  font-size: 0.875rem;
  transition: background-color 0.2s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.context-menu-item:hover {
  background: #4a5568;
  color: #fff;
}

.context-menu-item:active {
  background: #2d3748;
}

.shashin-icon {
  font-size: 0.9rem;
  flex-shrink: 0;
  min-width: 2rem;
  width: auto;
  text-align: left;
  line-height: 1;
  white-space: nowrap;
  display: inline-block;
}

.move-eval-icon {
  font-size: 1rem;
  flex-shrink: 0;
  width: 1.5rem;
  text-align: center;
  line-height: 1;
  display: inline-block;
}

.promotion-item {
  background: #1e3a8a;
  color: #dbeafe;
  border-bottom: 1px solid #3b82f6;
}

.promotion-item:hover {
  background: #1d4ed8;
  color: #fff;
}

.promotion-icon {
  font-size: 1rem;
  flex-shrink: 0;
  width: 1.5rem;
  text-align: center;
  line-height: 1;
  display: inline-block;
}

.delete-item {
  background: #dc2626;
  color: #fecaca;
  border-bottom: 1px solid #ef4444;
}

.delete-item:hover {
  background: #b91c1c;
  color: #fff;
}

.delete-icon {
  font-size: 1rem;
  flex-shrink: 0;
  width: 1.5rem;
  text-align: center;
  line-height: 1;
  display: inline-block;
}

@keyframes slideDown {
  from {
    opacity: 0;
    max-height: 0;
  }
  to {
    opacity: 1;
    max-height: 500px;
  }
}
</style>
