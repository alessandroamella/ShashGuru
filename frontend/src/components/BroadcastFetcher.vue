<script setup>
import { ref } from 'vue'
import EventGame from './EventGame.vue'

const eventId = ref('sO7W9Jje')      // Example tournament ID
const roundId = ref('')              // Set directly or extract from URL
const pgnList = ref([])
const loading = ref(false)
const error = ref(null)

// Fetch tournament info and list of rounds
async function fetchEvent() {
  error.value = null
  try {
    const res = await fetch(`https://lichess.org/api/broadcast/${eventId.value}`)
    if (!res.ok) throw new Error('Event not found')
    const data = await res.json()
    console.log('Event data:', data)

    // Pick default round if available
    roundId.value = data.defaultRoundId || (data.rounds[0] && data.rounds[0].id) || ''
  } catch (err) {
    error.value = err.message
  }
}

function splitPGNs(pgnText) {
    //Takes the full PGN list from the Lichess API and splits it into individual games
  return pgnText
    .trim()
    .split(/\n\n(?=\[Event )/) // lookahead to keep "[Event" with each game
}

// Fetch PGNs of a specific round
async function fetchPgn() {
  if (!roundId.value) return
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`https://lichess.org/api/broadcast/round/${roundId.value}.pgn`)
    if (!res.ok) throw new Error('Could not fetch PGN')
    const pgnText = await res.text()
    pgnList.value = splitPGNs(pgnText)
    console.log('Fetched PGN:', pgnList.value)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

// Helper: If user pastes a broadcast URL, extract IDs
function setFromUrl(url) {
  // Example URL: https://lichess.org/broadcast/knight-invitational/sO7W9Jje/eJLgkG7n
  const parts = url.split('/')
  eventId.value = parts[5] || ''
  roundId.value = parts[6] || ''
}
</script>

<template>
  <div class="p-4" >
    <h2 class="text-xl font-bold mb-2">🎯 Lichess Broadcast Fetcher</h2>

    <div class="mb-4">
      <label class="block font-semibold">Event ID:</label>
      <input v-model="eventId" placeholder="Enter eventId (e.g. sO7W9Jje)" class="border p-1 rounded w-full" />
      <button @click="fetchEvent" class="px-3 py-1 rounded mt-2">Fetch Event Info</button>
    </div>

    <div class="mb-4">
      <label class="block font-semibold">Round ID:</label>
      <input v-model="roundId" placeholder="Enter roundId (e.g. eJLgkG7n)" class="border p-1 rounded w-full" />
      <button @click="fetchPgn" class="px-3 py-1 rounded mt-2">Fetch PGNs</button>
    </div>

    <div class="mb-4">
      <label class="block font-semibold">Or Paste Broadcast URL:</label>
      <input @change="setFromUrl($event.target.value)" placeholder="https://lichess.org/broadcast/.../eventId/roundId" class="border p-1 rounded w-full" />
    </div>

    <div v-if="loading">⏳ Loading PGN...</div>
    <div v-if="error" class="text-red-500">⚠️ {{ error }}</div>
    <pre v-if="pgnList" class="bg-gray-100 p-2 rounded whitespace-pre-wrap text-sm"></pre>
    
  </div>
  <div  class="d-flex flex-row flex-wrap  mx-5">
        <EventGame :pgn="pgn"
        v-for="pgn in pgnList" :key="pgn.index" 
        class="flex-item"/>
    </div>
</template>
