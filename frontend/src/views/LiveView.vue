<script setup>
import { onMounted, ref } from 'vue'
import EventGame from '@/components/EventGame.vue'

const eventId = ref('sO7W9Jje')      // Example tournament ID
const roundId = ref('')              // Set directly or extract from URL
const pgnListFeatured = ref([])
const pgnListAsked = ref([])
const loading = ref(false)
const error = ref(null)
const featuredEvent = ref(null)
const isFeatureVisibile = ref(true)
const isQueriedVisibile = ref(true)
const searchHasHappened = ref(false)
const searchInput = ref('')

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
    .split(/\n\n(?=\[Event )/) // lookahead for new game start
}

async function fetchQueriedPgn() {
  if (searchInput.value.startsWith('http') || searchInput.value.includes('lichess.org')) {
    console.log("Setting from URL")
    setFromUrl(searchInput.value) // Extract IDs from URL
  } else {
    roundId.value = searchInput.value.trim()
  }
  if (roundId.value) {
    console.log("roundId.value", roundId.value)
    const pgnAsked = await fetchPgn(roundId.value)
    console.log('Queried PGN:', pgnAsked)
    if (pgnAsked) {
      pgnListAsked.value = splitPGNs(pgnAsked)
      console.log('Fetched Queried PGN:', pgnListAsked.value)
      if (!searchHasHappened.value) {
        searchHasHappened.value = true
      }
    }
  }
}

async function fetchPgnFeatured() {
  if (!featuredEvent.value) return
  const pgnFeatured = await fetchPgn(featuredEvent.value)
  if (pgnFeatured !== null) {
    pgnListFeatured.value = splitPGNs(pgnFeatured)
    console.log('Fetched Featured Event PGN:', pgnListFeatured.value)
  }
}


// Fetch PGNs of a specific round
async function fetchPgn(idToFetch) {
  let pgnText = '';
  loading.value = true
  error.value = null
  try {
    const res = await fetch(`https://lichess.org/api/broadcast/round/${idToFetch}.pgn`)
    if (!res.ok) throw new Error('Could not fetch PGN')
    pgnText = await res.text()
    console.log('Fetched PGN:', pgnText)
    loading.value = false
    return pgnText
  } catch (err) {
    error.value = err.message
    loading.value = false
    return null
  }
}

// Helper: If user pastes a broadcast URL, extract IDs
function setFromUrl(url) {
  try {
    // Example URL: https://lichess.org/broadcast/knight-invitational/sO7W9Jje/eJLgkG7n
    const parts = url.split('/')
    eventId.value = parts[5] || ''
    roundId.value = parts[6].split('#')[0] || ''
  } catch (err) {
    error.value = 'Invalid URL format'
  }

}

onMounted(() => {
  // Automatically fetch event info on mount
  featuredEvent.value = import.meta.env.FEATURED_EVENT_ID || 'KuHOrw9a' // Test featured event ID, should be null in production
  fetchPgnFeatured();
  //fetchTopEvents();
})

</script>

<template>

  <div class="p-4 mx-5">
    <div class="container py-4 w-100">
      <h2 class="text-center text-light mb-4 mx">Events and Broadcasts</h2>

      <!-- Search Bar -->
      <div id="search-group" class="input-group rounded-pill  p-1">
        <input id="input-event" type="text" class="form-control outline-none rounded-pill me-1" v-model="searchInput"
          @keyup.enter="fetchQueriedPgn" placeholder="Paste Lichess Broadcast URL or Event ID..." />

        <!-- Search Button -->
        <button id="search-button" class="btn rounded-circle" type="button" @click="fetchQueriedPgn"
          :disabled="loading">
          <span class="material-icons mt-1" v-if="!loading">search</span>
          <span v-else class="spinner-border spinner-border-sm"></span>
        </button>
      </div>

      <!-- Helper text -->
      <small id="helper" class="form-text  mt-2 ms-1">
        Example: https://lichess.org/broadcast/.../sO7W9Jje/eJLgkG7n or eJLgkG7n
      </small>

      <!-- Error Message -->
      <div v-if="error" class="text-danger mt-3">
        ⚠️ {{ error }}
      </div>
    </div>
  </div>


  <!-- Search results -->
  <div v-if="searchHasHappened" class="d-flex flex-row align-items-start p-3 ms-5 cursor-pointer"
    @click="isQueriedVisibile = !isQueriedVisibile">
    <div class="fs-3 flex-shrink-0">
      Your Event<span class="material-icons ms-1">{{ isQueriedVisibile ? 'keyboard_arrow_down' : 'chevron_right'
        }}</span>
    </div>
  </div>

  <!-- Transition wrapper -->
  <transition name="slide">
    <div v-if="(roundId !== null && roundId !== '') && isQueriedVisibile" class="d-flex flex-row flex-wrap mx-5">
      <EventGame :pgn="pgn" v-for="pgn in pgnListAsked" :key="pgn.index" class="flex-item" />
    </div>
  </transition>

  <!-- Featured event -->
  <div class="d-flex flex-row align-items-start p-3 ms-5 cursor-pointer"
    @click="isFeatureVisibile = !isFeatureVisibile">
    <div class="fs-3 flex-shrink-0">
      <span> Featured Events</span><span class="material-icons ms-1">{{ isFeatureVisibile ? 'keyboard_arrow_down' :
        'chevron_right'
        }}</span>
    </div>
  </div>

  <!-- Transition wrapper -->
  <transition name="slide">
    <div v-if="featuredEvent && isFeatureVisibile" class="d-flex flex-row justify-content-start flex-wrap mx-5">
      <EventGame :pgn="pgn" v-for="pgn in pgnListFeatured" :key="pgn.index" class="flex-item" />
    </div>
  </transition>
</template>


<style scoped>
#search-group,
#input-event {
  background-color: #232323 !important;
  border: none !important;
  color: white;
  outline: none;
  box-shadow: none;
}

#search-group {
  border: 1px solid #aaa23a !important;
}

#helper,
#input-event::placeholder {
  color: #ebebeba3;
}

#search-button {
  background-color: #aaa23a !important;
  border: 1px solid #aaa23a !important;
  color: white;
}

.cursor-pointer {
  cursor: pointer;
}

.transition-transform {
  transition: transform 0.3s ease;
}

.rotate-90 {
  transform: rotate(90deg);
}

.toggle-arrow {
  font-size: 1.5rem;
  /* make icon size match your text */
  line-height: 1;
  /* removes extra vertical padding */
  vertical-align: middle;
}

.slide-enter-active,
.slide-leave-active {
  transition: max-height 0.3s ease, opacity 0.3s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  max-height: 0;
  opacity: 0;
}

.slide-enter-to,
.slide-leave-from {
  max-height: 1000px;
  /* something large enough for your content */
  opacity: 1;
}
</style>