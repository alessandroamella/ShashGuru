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
          >
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
          >
            {{ moveItem.blackMove.move }}
          </span>
          <span v-else class="move-text empty">...</span>
        </div>

        <!-- Variation -->
        <div v-else-if="moveItem.type === 'variation'" class="variation-item">
          <div class="variation-line">
            <span class="variation-marker">(</span>
            <span class="variation-start">{{ getVariationStart(moveItem.variation) }}</span>
            <MoveTreeDisplay 
              :node="moveItem.variation"
              :currentNode="currentNode"
              :selectedPath="selectedPath"
              :level="level + 1"
              :isAnalysisMode="isAnalysisMode"
              @nodeClicked="$emit('nodeClicked', $event)"
              @addMove="$emit('addMove', $event)"
            />
            <span class="variation-marker">)</span>
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
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue';

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
  }
});

const emit = defineEmits(['nodeClicked', 'addMove']);

const newMove = ref('');
const moveInput = ref(null);

// Create display items that include both moves and variations in proper order
const displayItems = computed(() => {
  if (!props.node) return [];
  
  const items = [];
  buildDisplayItems(props.node, items, 0);
  return items;
});

// Check if current node is in this tree
const isCurrentNodeInTree = computed(() => {
  if (!props.currentNode || !props.node) return false;
  return isNodeInTree(props.currentNode, props.node);
});

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

function getVariationStart(variationNode) {
  // Calculate move number for variation start
  let count = 0;
  let current = variationNode;
  while (current.parent) {
    count++;
    current = current.parent;
  }
  
  const moveNumber = Math.ceil(count / 2);
  const isBlackMove = count % 2 === 0;
  
  if (isBlackMove) {
    return `${moveNumber}...${variationNode.move}`;
  } else {
    return `${moveNumber}.${variationNode.move}`;
  }
}

async function handleAddMove() {
  if (newMove.value.trim()) {
    emit('addMove', newMove.value.trim());
    newMove.value = '';
  }
}

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
  font-size: 0.8em;
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
}

.variation-marker {
  color: #6c757d;
  font-weight: bold;
  margin: 0 0.25rem;
  flex-shrink: 0;
}

.variation-start {
  color: #adb5bd;
  font-weight: 500;
  margin-right: 0.5rem;
  flex-shrink: 0;
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

/* Nested variations get deeper indentation */
.variation-item .move-tree-display {
  margin-left: 0;
}

.variation-item .variation-item {
  margin-left: 1rem;
}
</style>
