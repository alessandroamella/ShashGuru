<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const broadcasts = ref([])
const gamesPgn = ref('')
const loading = ref(false)
let pollInterval = null

// Fetch official broadcasts
async function fetchBroadcasts() {
  try {
    const res = await fetch('https://lichess.org/api/broadcast?nb=5')
    const text = await res.text()

    // Lichess returns NDJSON (newline-delimited JSON)
    broadcasts.value = text
      .trim()
      .split('\n')
      .map((line) => JSON.parse(line))
  } catch (err) {
    console.error('Error fetching broadcasts:', err)
  }
}

// Poll PGNs from a specific round
async function pollRoundPgn(roundId) {
  if (!roundId) return

  loading.value = true
  try {
    const res = await fetch(`https://lichess.org/api/broadcast/round/${roundId}.pgn`)
    const pgnText = await res.text()
    gamesPgn.value = pgnText
  } catch (err) {
    console.error('Error fetching PGN:', err)
  } finally {
    loading.value = false
  }
}

// Start polling every x seconds
function startPolling(roundId) {
  stopPolling()
  pollRoundPgn(roundId) // initial fetch
  pollInterval = setInterval(() => pollRoundPgn(roundId), 1000000)
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// Example: Automatically start with the first broadcast's default round
onMounted(async () => {
  await fetchBroadcasts()
  if (broadcasts.value.length > 0) {
    const first = broadcasts.value[0]
    if (first.defaultRoundId) {
      startPolling(first.defaultRoundId)
    }
  }
})

onUnmounted(() => stopPolling())
</script>

<template>
  <div class="p-4">
    <h2 class="text-xl font-bold mb-2">📡 Lichess Broadcasts</h2>

    <ul class="mb-4">
      <li v-for="b in broadcasts" :key="b.tour.id">
        <strong>{{ b.tour.name }}</strong>
        <a :href="b.tour.url" target="_blank" class="text-blue-500">View</a>
      </li>
    </ul>

    <div v-if="loading">⏳ Fetching PGN...</div>
    <pre v-else class="bg-gray-100 p-2 rounded whitespace-pre-wrap text-sm">
      {{ gamesPgn }}
    </pre>
  </div>
</template>
