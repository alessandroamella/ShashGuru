<script setup>
import { Chess } from 'chess.js'
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import AIChat from '@/components/AIChat.vue'
import ChessBoard from '@/components/ChessBoard.vue'
import EngineLines from '@/components/EngineLines.vue'
import MoveTreeDisplay from '@/components/MoveTreeDisplay.vue'
import { DEFAULT_DEPTH, DEFAULT_SHOW_LINES } from '@/constants/evaluation.js'
import { EvaluationService } from '@/services/evaluationService.js'

// Helper per UUID
function generateUUID() {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    var r = (Math.random() * 16) | 0,
      v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

const fen = ref('')
const moves = ref([])
const isLoading = ref(false)
const isLoadingEvaluations = ref(false)
const hasPlayerInfo = ref(false)
const hasMoves = ref(false)
const selectedMoveIndex = ref(0)
const moveRefs = ref([])

// Live mode state
const myUserId = ref(localStorage.getItem('shashguru_uid') || generateUUID())
localStorage.setItem('shashguru_uid', myUserId.value)

const liveState = ref({
  controller_id: null,
  is_free: true,
  fen: '',
  chat: [],
})

const isController = computed(() => liveState.value.controller_id === myUserId.value)
const isSpectator = computed(() => !liveState.value.is_free && !isController.value)
const statusClass = computed(() => {
  if (isController.value) return 'bg-success'
  if (!liveState.value.is_free) return 'bg-danger'
  if (liveState.value.is_free) return 'bg-secondary'
  return 'bg-dark'
})
const pollingInterval = ref(null)

// Tree structure for moves
const moveTree = ref(null)
const currentNode = ref(null)
const selectedPath = ref([])
const isAnalysisMode = ref(false)

// Tab state
const activeTab = ref('moves')

// Engine evaluation data
const engineEvaluation = ref({
  bestMove: null,
  evaluation: null,
  depth: 0,
  lines: [],
})

// Loading state for engine evaluation from chessboard
const isEngineEvaluationLoading = ref(false)

// UI settings
const showLines = ref(DEFAULT_SHOW_LINES)
const evaluationDepth = ref(DEFAULT_DEPTH)

// Ref for AIChat component
const aiChatRef = ref(null)

// Funzioni live

async function pollLiveState() {
  try {
    const serverUrl = import.meta.env.BASE_URL + 'backend'
    const res = await fetch(`${serverUrl}/live/state`)
    const data = await res.json()

    liveState.value = data

    // Sync FEN if we are just watching
    if (!isController.value) {
      if (data.fen && data.fen !== fen.value) {
        // Prevent local updates from fighting server updates if we aren't controller
        fen.value = data.fen
      }
    }

    // REMOVED: The auto-claim logic
    // } else if (liveState.value.is_free) {
    //   claimController()
    // }
  } catch (e) {
    console.error('Polling error', e)
  }
}

// Add this new function to leave the game
async function leaveGame() {
  const serverUrl = import.meta.env.BASE_URL + 'backend'
  await fetch(`${serverUrl}/live/leave`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: myUserId.value }),
  })
  // The next pollLiveState will see that controller_id is null
}

// Ensure claimController is available (it likely already is in your code)
async function claimController() {
  const serverUrl = import.meta.env.BASE_URL + 'backend'
  const res = await fetch(`${serverUrl}/live/claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: myUserId.value }),
  })
  return await res.json()
}

async function pushUpdate(newFen, newChat = null) {
  if (!isController.value) return // Solo il controllore invia dati

  const serverUrl = import.meta.env.BASE_URL + 'backend'
  await fetch(`${serverUrl}/live/update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: myUserId.value,
      fen: newFen,
      chat: newChat,
    }),
  })
}

// Tree node structure for moves
class MoveNode {
  constructor(move = null, fen = null, parent = null) {
    this.move = move // The move in SAN notation
    this.fen = fen // The FEN after this move
    this.parent = parent // Parent node
    this.children = [] // Array of child nodes (variations)
    this.mainLine = null // Main continuation
    this.comment = '' // Move comment/annotation
    this.id = Math.random().toString(36).substr(2, 9) // Unique ID
  }

  addChild(move, fen) {
    const child = new MoveNode(move, fen, this)
    this.children.push(child)
    if (!this.mainLine) {
      this.mainLine = child
    }
    return child
  }

  addVariation(move, fen) {
    const variation = new MoveNode(move, fen, this)
    this.children.push(variation)
    return variation
  }

  getPath() {
    const path = []
    let current = this
    while (current.parent) {
      const parentIndex = current.parent.children.indexOf(current)
      path.unshift(parentIndex)
      current = current.parent
    }
    return path
  }
}

// Initialize the tree with starting position
function initializeTree() {
  const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
  moveTree.value = new MoveNode(null, startingFen)
  currentNode.value = moveTree.value
  selectedPath.value = []
}

// Convert linear moves to tree structure
function buildTreeFromMoves(movesList) {
  initializeTree()
  const chess = new Chess()
  let current = moveTree.value

  for (const move of movesList) {
    try {
      const chessMove = chess.move(move)
      if (chessMove) {
        current = current.addChild(chessMove.san, chess.fen())
      }
    } catch (e) {
      console.error('Invalid move:', move, e)
      break
    }
  }

  // Set current node to the last move
  currentNode.value = current
  selectedPath.value = current.getPath()

  // Fetch evaluations for all moves in the background
  fetchEvaluationsForMoves()

  return current
}

// Add a new move/variation to current position
function addMove(move) {
  if (!currentNode.value) return null

  const chess = new Chess(currentNode.value.fen)
  try {
    const chessMove = chess.move(move)
    if (chessMove) {
      // Check if this move already exists as a child
      const existingChild = currentNode.value.children.find((child) => child.move === chessMove.san)
      if (existingChild) {
        // Move to existing variation
        currentNode.value = existingChild
      } else {
        // If this is the first move from current position, make it the main line
        if (currentNode.value.children.length === 0) {
          const newNode = currentNode.value.addChild(chessMove.san, chess.fen())
          currentNode.value = newNode
          // Fetch evaluation for the new move
          // fetchEvaluationForNode(newNode);
        } else {
          // Add as new variation
          const newNode = currentNode.value.addVariation(chessMove.san, chess.fen())
          currentNode.value = newNode
          // Fetch evaluation for the new move
          // fetchEvaluationForNode(newNode);
        }
      }
      selectedPath.value = currentNode.value.getPath()
      updateFen(currentNode.value.fen)
      rebuildMovesDisplay()
      return currentNode.value
    }
  } catch (e) {
    console.error('Invalid move:', move, e)
  }
  return null
}

// Set Shashin position type for a move
function setShashinType(payload) {
  const { node, type } = payload
  if (node) {
    // Add the shashinType property to the node
    node.shashinType = type
    console.log(`Set Shashin type "${type}" for move: ${node.move}`)
  }
}

// Set move evaluation for a move
function setMoveEvaluation(payload) {
  const { node, type } = payload
  if (node) {
    // Add the moveEvaluation property to the node
    node.moveEvaluation = type
    console.log(`Set move evaluation "${type}" for move: ${node.move}`)
  }
}

// Fetch evaluation for a position
async function fetchEvaluationForNode(node) {
  if (!node || !node.fen) return null

  try {
    // Get depth and lines from UI settings
    const depth = evaluationDepth.value
    const lines = showLines.value || 1
    const evaluation = await EvaluationService.fetchEvaluation(node.fen, depth, lines)

    if (evaluation) {
      node.evaluation = evaluation
      console.log(`Fetched evaluation for move ${node.move}:`, evaluation)
      return evaluation
    }
  } catch (error) {
    console.error(`Error fetching evaluation for move ${node.move}:`, error)
  }

  return null
}

// Fetch evaluations for all moves in the current line
async function fetchEvaluationsForMoves() {
  if (!moveTree.value || isSpectator.value) return

  isLoadingEvaluations.value = true

  try {
    const mainLineMoves = getMainLineMoves()

    // Fetch evaluations for main line moves in parallel
    await Promise.all(
      mainLineMoves.map((node) => {
        if (!node.evaluation) {
          return fetchEvaluationForNode(node)
        }
        return Promise.resolve()
      }),
    )
  } finally {
    isLoadingEvaluations.value = false
  }
}

// Navigate to a specific node
function navigateToNode(node) {
  currentNode.value = node
  selectedPath.value = node.getPath()
  updateFen(node.fen)
}

// Get all moves in current main line
function getMainLineMoves() {
  const moves = []
  let current = moveTree.value
  while (current.mainLine) {
    current = current.mainLine
    moves.push(current)
  }
  return moves
}

// Rebuild the visual moves display
function rebuildMovesDisplay() {
  const mainLine = getMainLineMoves()
  moves.value = mainLine.map((node) => node.move)
  selectedMoveIndex.value = selectedPath.value.length > 0 ? selectedPath.value[0] : -1
}

// Metadata from PGN
const whitePlayer = ref('')
const blackPlayer = ref('')
const gameResult = ref('')

// Called when ChessBoard emits PGN (full)
function setMovesFromPGN(payload) {
  moveRefs.value = []
  if (payload.fullPGN !== null && payload.fullPGN !== '') {
    hasMoves.value = true
  } else {
    hasMoves.value = false
  }
  // Build tree from moves
  buildTreeFromMoves(payload.moves)
  hasMoves.value = true

  // Set player names and result
  if (payload.headers.White && payload.headers.Black) {
    whitePlayer.value = payload.headers.White
    blackPlayer.value = payload.headers.Black
    gameResult.value = payload.headers.Result || '-'
    if (gameResult.value === '*') {
      gameResult.value = 'Ongoing'
    } else if (gameResult.value === '1/2-1/2') {
      gameResult.value = '½-½'
    }
    hasPlayerInfo.value = true
  } else {
    whitePlayer.value = ''
    blackPlayer.value = ''
    gameResult.value = payload.headers.Result || '-'
  }

  // Navigate to the beginning of the game, before any move
  navigateToNode(moveTree.value)

  rebuildMovesDisplay()
}

// Navigation functions

function backStart() {
  navigateToNode(moveTree.value)
  rebuildMovesDisplay()
}

function backOneMove() {
  if (currentNode.value && currentNode.value.parent) {
    navigateToNode(currentNode.value.parent)
    rebuildMovesDisplay()
  }
}

function forwardOneMove() {
  if (currentNode.value) {
    // If there's a mainLine, go there first
    if (currentNode.value.mainLine) {
      navigateToNode(currentNode.value.mainLine)
      rebuildMovesDisplay()
    }
    // Otherwise, if there are children, go to the first child
    else if (currentNode.value.children.length > 0) {
      navigateToNode(currentNode.value.children[0])
      rebuildMovesDisplay()
    }
  }
}

function forwardEnd() {
  const mainLine = getMainLineMoves()
  if (mainLine.length > 0) {
    navigateToNode(mainLine[mainLine.length - 1])
    rebuildMovesDisplay()
  }
}

// Detects if an element is editable, needed to prevent arrow key event being stealed from input/textarea
function isEditableElement(el) {
  return el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)
}

// Arrow key navigation
function handleKeyDown(event) {
  if (isLoading.value) return

  if (isEditableElement(document.activeElement)) return // Ignore if focused on input/textarea, otherwise it steals every arrow key event

  switch (event.key) {
    case 'ArrowLeft':
      event.preventDefault()
      backOneMove()
      break
    case 'ArrowRight':
      event.preventDefault()
      forwardOneMove()
      break
    case 'ArrowUp':
      event.preventDefault()
      // Go to beginning
      backStart()
      break
    case 'ArrowDown':
      event.preventDefault()
      // Go to end
      forwardEnd()
      break
    case 'Home':
      event.preventDefault()
      backStart()
      break
    case 'End':
      event.preventDefault()
      forwardEnd()
      break
    case 'Enter':
      if (event.shiftKey) {
        event.preventDefault()
        toggleAnalysisMode()
      }
      break
  }
}


function toggleAnalysisMode() {
  isAnalysisMode.value = !isAnalysisMode.value
}

function switchTab(tab) {
  activeTab.value = tab
}

async function updateFen(newFen) {
  fen.value = newFen
  if (isController.value) {
    pushUpdate(newFen, null)
  } else if (liveState.value.is_free) {
    // Auto-claim if free
    const res = await claimController()
    if (res.success) {
      liveState.value.controller_id = myUserId.value
      liveState.value.is_free = false
      pushUpdate(newFen, null)
    }
  }
}

function handleLoadingChat(val) {
  isLoading.value = val
}

// Handle moves made on the board
function handleMoveAdded(moveData) {
  if (addMove(moveData.move)) {
    hasMoves.value = true
  }
}

// Handle engine evaluation updates
function handleEngineEvaluationUpdate(evalData) {
  engineEvaluation.value = evalData
}

// Handle showLines setting updates
function handleShowLinesUpdate(newValue) {
  showLines.value = newValue
}

// Handle depth setting updates
function handleDepthUpdate(newValue) {
  evaluationDepth.value = newValue
}

// Handle engine evaluation loading updates
function handleEvaluationLoadingUpdate(isLoading) {
  isEngineEvaluationLoading.value = isLoading
}

// Handle engine line move clicks
function handleEngineLineMove(move, line, moveIndex) {
  console.log('Engine line move clicked:', move, line, moveIndex)

  // Add the move from the engine line
  if (addMove(move)) {
    hasMoves.value = true
  }
}

// Promote a variation to main line
function promoteVariation(nodeToPromote) {
  console.log('promoteVariation called with node:', nodeToPromote)

  if (!nodeToPromote || !nodeToPromote.parent) {
    console.log('Cannot promote: node has no parent')
    return
  }

  const parent = nodeToPromote.parent
  const currentMainLine = parent.mainLine

  console.log('Promotion details:', {
    nodeToPromote: nodeToPromote.move,
    currentMainLine: currentMainLine?.move,
    parentChildren: parent.children.map((c) => c.move),
  })

  // Find the root of the variation that contains this node
  let variationRoot = nodeToPromote

  // If this node is already the direct main line, we need to find the variation root
  // by looking at the parent's children to find which one is not the main line
  if (currentMainLine === nodeToPromote) {
    // This shouldn't happen if our canPromoteToMainLine logic is correct
    console.log('Node is already main line, checking path...')

    // Check if this is actually on the main line path from root
    if (isNodeOnMainLinePath(nodeToPromote)) {
      console.log('Node is on main line path, cannot promote')
      return
    }
  }

  // Find the actual variation root by traversing up until we find a node
  // whose parent's main line is different
  while (variationRoot.parent && variationRoot.parent.mainLine === variationRoot) {
    variationRoot = variationRoot.parent
  }

  // Now variationRoot should be the first move of the variation
  if (variationRoot.parent) {
    const variationParent = variationRoot.parent

    // Swap the main line
    variationParent.mainLine = variationRoot

    console.log(
      `Successfully promoted variation starting with "${variationRoot.move}" to main line`,
    )
  } else {
    // Direct promotion case
    parent.mainLine = nodeToPromote
    console.log(`Successfully promoted move "${nodeToPromote.move}" to main line`)
  }

  // Rebuild the moves display to reflect the new main line
  rebuildMovesDisplay()

  // Update the selected path since the tree structure changed
  selectedPath.value = currentNode.value.getPath()

  // Force a reactive update
  moveTree.value = { ...moveTree.value }
}

// Check if a node is on the main line path from root to end
function isNodeOnMainLinePath(node) {
  if (!node || !node.parent) return true // Root is always on main line path

  // Traverse up to check if this node is always the main line of its parent
  let current = node
  while (current.parent) {
    if (current.parent.mainLine !== current) {
      return false
    }
    current = current.parent
  }

  return true
}

// Delete a move and all subsequent moves
function deleteMove(nodeToDelete) {
  console.log('deleteMove called with node:', nodeToDelete)

  if (!nodeToDelete || !nodeToDelete.parent) {
    console.log('Cannot delete: node has no parent (root node)')
    return
  }

  const parent = nodeToDelete.parent

  // Remove the node from parent's children array
  const childIndex = parent.children.indexOf(nodeToDelete)
  if (childIndex !== -1) {
    parent.children.splice(childIndex, 1)

    // If this was the main line, update the main line
    if (parent.mainLine === nodeToDelete) {
      // Set the main line to the next available child, or null if no children
      parent.mainLine = parent.children.length > 0 ? parent.children[0] : null
    }

    console.log(`Successfully deleted move "${nodeToDelete.move}" and all subsequent moves`)

    // If the current node was the deleted node or a descendant, navigate to the parent
    if (isNodeInDeletedSubtree(currentNode.value, nodeToDelete)) {
      navigateToNode(parent)
    }

    // Rebuild the moves display to reflect the changes
    rebuildMovesDisplay()

    // Update the selected path since the tree structure changed
    selectedPath.value = currentNode.value.getPath()

    // Force a reactive update
    moveTree.value = { ...moveTree.value }
  } else {
    console.log('Error: Node not found in parent children')
  }
}

// Check if a node is in the subtree that's being deleted
function isNodeInDeletedSubtree(nodeToCheck, deletedRoot) {
  if (!nodeToCheck || !deletedRoot) return false

  let current = nodeToCheck
  while (current) {
    if (current.id === deletedRoot.id) {
      return true
    }
    current = current.parent
  }
  return false
}

// Mount/unmount handlers
onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
  initializeTree()

  // Start Polling
  pollLiveState() // Primo check immediato
  pollingInterval.value = setInterval(pollLiveState, 1000) // Check ogni secondo
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  if (pollingInterval.value) clearInterval(pollingInterval.value)
})

function handleSystemReset() {
  console.log("System Hard Reset Triggered")
  
  // 1. Resetta Chat AI (interrompe anche le chiamate di rete)
  if (aiChatRef.value) {
    aiChatRef.value.resetChat()
  }

  // 2. Resetta l'albero delle mosse
  initializeTree()
  rebuildMovesDisplay()
  hasMoves.value = false
  
  // 3. Resetta le valutazioni del motore
  engineEvaluation.value = {
    bestMove: null,
    evaluation: null,
    depth: 0,
    lines: [],
  }
  isEngineEvaluationLoading.value = false
  
  // 4. Resetta metadati giocatore
  whitePlayer.value = ''
  blackPlayer.value = ''
  gameResult.value = ''
  hasPlayerInfo.value = false

  // 5. Opzionale: Resetta la FEN alla posizione iniziale
  const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
  updateFen(startingFen)
}

watch(selectedMoveIndex, async () => {
  await nextTick()
  const el = moveRefs.value[selectedMoveIndex.value]
  if (el) {
    el.scrollIntoView({
      behaviour: 'smooth',
      block: 'nearest',
      inline: 'nearest',
    })
  }
})
</script>

<template>
  <!-- Control Bar -->
  <div class="d-flex justify-content-between align-items-center w-100 p-2 text-white fw-bold" :class="statusClass">
    <!-- Left: Reset Button -->
    <div class="ms-3">
      <button class="btn btn-sm btn-danger border border-white fw-bold d-flex align-items-center gap-1 shadow" @click="handleSystemReset" title="Reset everything (Fix stuck analysis)">
        <i class="material-icons" style="font-size: 16px;">restart_alt</i> 
        <span class="d-none d-sm-inline">Reset System</span>
      </button>
    </div>
    
    <!-- Center: Status/Control -->
    <div class="grow d-flex justify-content-center">
      <!-- Case 1: I am the player -->
      <div v-if="isController" class="d-flex align-items-center gap-2 gap-md-3 flex-wrap justify-content-center">
        <span class="text-center">You are playing (Controller)</span>
        <button class="btn btn-sm btn-light text-danger fw-bold" @click="leaveGame">
          Stop playing (Spectate)
        </button>
      </div>
      <!-- Case 2: Someone else is playing -->
      <div v-else-if="!liveState.is_free && !isController" class="text-center">
        SPECTATOR MODE: Another user is playing
      </div>
      <!-- Case 3: The spot is free -->
      <div v-else-if="liveState.is_free" class="d-flex align-items-center gap-2 gap-md-3 flex-wrap justify-content-center">
        <span>The board is free</span>
        <button class="btn btn-sm btn-success fw-bold" @click="claimController">
          Join game (Play)
        </button>
      </div>
      <!-- Case 4: Connecting -->
      <div v-else class="text-center">Connecting...</div>
    </div>
    
    <!-- Right: Spacer to balance left button -->
    <div class="me-3" style="width: 140px;"></div>
  </div>

  <div id="chessboard" class="d-flex flex-column flex-lg-row justify-content-evenly m-2 m-lg-5">
    <div class="flex-item mx-0 p-3 pt-0" :class="{ loading: isLoading }">
      <ChessBoard :fenProp="fen" :viewOnly="!isController" @updateFen="updateFen" @setMovesFromPGN="setMovesFromPGN"
        @moveAdded="handleMoveAdded" @engineEvaluationUpdate="handleEngineEvaluationUpdate"
        @showLinesUpdate="handleShowLinesUpdate" @evaluationLoadingUpdate="handleEvaluationLoadingUpdate"
        @depthUpdate="handleDepthUpdate" />
    </div>

    <div class="right-panel d-flex flex-column flex-lg-row flex-fill mx-2 mx-lg-5 gap-3">
      <!-- TABBED PANEL -->
      <div id="tabbed-panel" class="tabbed-section rounded-4 d-flex flex-column rounded-top-4 overflow-hidden">
        <!-- TAB NAVIGATION -->
        <div class="tab-navigation d-flex">
          <button class="tab-button flex-fill py-2 px-3 border-0 fw-bold"
            :class="{ 'tab-active': activeTab === 'moves', 'tab-inactive': activeTab !== 'moves' }"
            @click="switchTab('moves')">
            <i class="material-icons me-1" style="font-size: 18px">sports_esports</i>
            Moves
          </button>
          <button class="tab-button flex-fill py-2 px-3 border-0 fw-bold"
            :class="{ 'tab-active': activeTab === 'chat', 'tab-inactive': activeTab !== 'chat' }"
            @click="switchTab('chat')">
            <i class="material-icons me-1" style="font-size: 18px">chat</i>
            AI Chat
          </button>
        </div>

        <!-- TAB CONTENT -->
        <div class="tab-content flex-fill d-flex flex-column overflow-hidden">
          <!-- MOVES TAB -->
          <div class="tab-pane flex-fill d-flex flex-column overflow-hidden">
            <!-- PLAYER INFO -->
            <div v-if="hasPlayerInfo" id="playerInfo"
              class="d-flex align-items-center justify-content-between p-3 text-light" style="
                background-color: #33312e;
                border-bottom: 1px solid #ffffff1e;
                max-height: 100px;
              ">
              <!-- White Player -->
              <div class="text-truncate text-center" style="flex: 1; padding-right: 1rem">
                <div class="fw-bold fs-6">White:</div>
                <div class="fs-6 text-truncate">{{ whitePlayer }}</div>
              </div>

              <!-- Game Result  -->
              <div class="shrink-0 mx-auto px-2">
                <div class="fs-4 fw-bold">{{ gameResult }}</div>
              </div>

              <!-- Black Player -->
              <div class="text-truncate text-center" style="flex: 1; padding-left: 1rem">
                <div class="fw-bold fs-6">Black:</div>
                <div class="fs-6 text-truncate">{{ blackPlayer }}</div>
              </div>
            </div>

            <!-- MOVES -->
            <div v-if="activeTab === 'moves'" class="flex-fill">
              <div id="moveHeader" class="d-flex justify-content-center align-items-center py-1 shrink-0">
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!currentNode || !currentNode.parent"
                    @click="backStart">
                    first_page
                  </button>
                </div>
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!currentNode || !currentNode.parent"
                    @click="backOneMove">
                    arrow_back
                  </button>
                </div>
                <span class="fs-6 fw-bold text-center mx-2">
                  <span v-if="isAnalysisMode" class="badge bg-warning text-dark ms-1">Analysis</span>
                </span>
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!currentNode || !currentNode.mainLine"
                    @click="forwardOneMove">
                    arrow_forward
                  </button>
                </div>
                <div>
                  <button class="btn btn-sm text-white material-icons" :disabled="!currentNode || !currentNode.mainLine"
                    @click="forwardEnd">
                    last_page
                  </button>
                </div>
                <div class="ms-1">
                  <button class="btn btn-sm" :class="isAnalysisMode ? 'btn-warning' : 'btn-outline-light'"
                    @click="toggleAnalysisMode" title="Toggle Analysis Mode (Shift+Enter)">
                    <i class="material-icons" style="font-size: 18px">analytics</i>
                  </button>
                </div>
                <div class="ms-1">
                  <button class="btn btn-sm btn-outline-info" @click="fetchEvaluationsForMoves"
                    :disabled="isLoadingEvaluations" title="Fetch Evaluations">
                    <span v-if="isLoadingEvaluations" class="spinner-border spinner-border-sm me-1"
                      role="status"></span>
                    <i class="material-icons" style="font-size: 18px">assessment</i>
                  </button>
                </div>
              </div>
              <div class="flex-fill overflow-auto">
                <div id="moves" class="px-3 pt-3 pb-2 h-100">
                  <!-- Engine Lines Display -->
                  <EngineLines v-if="
                    (engineEvaluation &&
                      engineEvaluation.lines &&
                      engineEvaluation.lines.length > 0) ||
                    isEngineEvaluationLoading
                  " :lines="engineEvaluation.lines" :maxLines="showLines" :depth="engineEvaluation.depth"
                    :currentFen="currentNode?.fen || ''" :loading="isEngineEvaluationLoading"
                    @move-clicked="handleEngineLineMove" class="mb-3" />
                  <div v-if="hasMoves" class="move-tree shadow">
                    <div class="moves-header rounded-top">
                      <span class="header-text fs-6">Moves</span>
                    </div>
                    <div class="moves-body ps-2 rounded-bottom">
                      <MoveTreeDisplay :node="moveTree" :currentNode="currentNode" :selectedPath="selectedPath"
                        :engineEvaluation="engineEvaluation" :showLines="showLines"
                        :isEvaluationLoading="isEngineEvaluationLoading" @nodeClicked="navigateToNode"
                        @addMove="addMove" @setShashinType="setShashinType" @setMoveEvaluation="setMoveEvaluation"
                        @promoteVariation="promoteVariation" @deleteMove="deleteMove"
                        :isAnalysisMode="isAnalysisMode" />
                    </div>
                  </div>
                  <div v-if="!hasMoves && !isAnalysisMode" class="text-secondary text-center">
                    Load a PGN or make moves on the board to begin analysis
                  </div>
                  <div v-if="!hasMoves && isAnalysisMode" class="text-secondary text-center">
                    <i class="material-icons me-2">info</i>Analysis mode enabled - make moves on the
                    board or use arrow keys to navigate
                  </div>
                </div>
              </div>
            </div>

            <!-- CHAT TAB -->
            <div v-if="activeTab === 'chat'" id="chat-view"
              class="tab-pane chat-section flex-fill rounded-4 d-flex flex-column">
              <!-- Pass allowInteraction prop here -->
              <AIChat 
                ref="aiChatRef" 
                :fen="fen" 
                :depth="evaluationDepth" 
                :allowInteraction="!isSpectator"
                @loadingChat="handleLoadingChat" 
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tabbed-section {
  background-color: #262421;
  min-width: 600px;
  height: 80vh;
  flex: 1;
}

.tab-navigation {
  background-color: #1a1916;
  border-bottom: 1px solid #3a3a3a;
  border-top-right-radius: 1em;
  border-top-left-radius: 1em;
}

.tab-button {
  background-color: transparent;
  color: #b2b2b2;
  transition: all 0.3s ease;

  border-bottom: 3px solid transparent !important;
}

.tab-button:hover {
  background-color: #2a2824;
  color: #e8e8e8;
}

.tab-active {
  background-color: #2f2d2a !important;
  color: #aaa23a !important;
  border-bottom: 3px solid #aaa23a !important;
  border-top-right-radius: 1em;
  border-top-left-radius: 1em;
}

.tab-inactive {
  background-color: #262421;
  border-top-right-radius: 1em;
  border-top-left-radius: 1em;
  border-bottom: 3px solid #262421 !important;
}

.tab-content {
  background-color: #262421;
}

.tab-pane {
  overflow: hidden;
}

.moves-section {
  background-color: #262421;
  min-width: 350px;
  max-width: 500px;
  height: 80vh;
  flex: 0 0 auto;
}

.chat-section {
  background-color: #262421;
  min-width: 400px;
  flex: 1;
}

.moves-header {
  background-color: #444;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-text {
  color: #e8e8e8;
  font-weight: 600;
  font-size: 0.9rem;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.moves-body {
  border: 1px solid #444;
  border-top: 0px solid transparent;
  margin-bottom: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 60vh;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  padding: 8px 0;
  scrollbar-width: thin;
  scrollbar-color: #888 transparent;
}

.right-panel {
  height: 80vh;
}

#chessboard {
  color: aliceblue;
  height: 50%;
}

.selected>.colorize {
  background-color: #cdd26a;
  color: black;
  border-radius: 4px;
  user-select: none;
}

.loading {
  pointer-events: none;
  /* Prevent all interaction */
}

#moves {
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  border-bottom: 1px solid #ffffff1e;
  line-height: 1.6;
  scrollbar-width: thin;
  scrollbar-color: #888 transparent;
}

.move-tree {
  font-family: 'Courier New', monospace;
}

#moveHeader {
  background-color: #2f2d2a;
  border-bottom: 1px solid #ffffff1e;
}

#moveHeader button {
  border: none;
}

#playerInfo {
  background-color: #33312e;
  border-bottom: 1px solid #ffffff1e;
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
</style>
