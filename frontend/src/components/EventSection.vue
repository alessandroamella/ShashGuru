<template>
    <div v-if="shouldRender" class="card-like event-section mx-5 mb-2 pb-3 position-relative">
        <div class="d-flex flex-row align-items-start p-3 cursor-pointer event-header" @click="toggleVisibility">
            <div class="fs-4 flex-shrink-0">
                <span>{{ title }}</span>
                <span class="material-icons ms-1">
                    {{ isVisible ? 'keyboard_arrow_down' : 'chevron_right' }}
                </span>
            </div>
        </div>

        <!-- Body -->
        <transition name="slide">
            <div v-if="isVisible" class="d-flex flex-row flex-wrap event-body">

                <template v-if="isLoading">
                    <EventGameSkeleton v-for="i in 3"
                        :key="`skeleton-${i}`" />
                </template>

                <template v-else>
                    <EventGame v-for="(pgn, index) in pgnListToRender" :key="`pgn-${index}`" :pgn="pgn"
                        class="flex-item shadow" />
                </template>

            </div>
        </transition>
        <span v-if="isVisible && (pgnListToRender.length < pgnList.length) && !isLoading" class="material-icons-outlined"
            id="load-more" @click="loadMore" title="Show more">
            add
        </span>
        
    </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import EventGame from './EventGame.vue'
import EventGameSkeleton from './EventGameSkeleton.vue'


const props = defineProps({
    title: { type: String, required: true },
    pgnList: { type: Array, default: () => [] },
    shouldRender: { type: Boolean, default: true },
    initiallyOpen: { type: Boolean, default: false }
})
const isVisible = ref(props.initiallyOpen)
const pgnListToRender = ref([])
const isLoading = ref(false)

function add5() {
    setTimeout(() => {
        const currentLength = pgnListToRender.value.length
        const nextBatch = props.pgnList.slice(currentLength, currentLength + 5)

        if (nextBatch.length > 0) {
            pgnListToRender.value.push(...nextBatch)
        }
        isLoading.value = false
        
    }, 100)
    
}

// Watch for changes to pgnList with debouncing
watch(() => props.pgnList, (newPgnList, oldPgnList) => {
    if (isLoading.value) return

    // Reset if the list changes significantly
    if (!oldPgnList || newPgnList.length !== oldPgnList.length) {
        pgnListToRender.value = []
    }

    add5()
}, { immediate: true })

// Function to load more items manually
const loadMore = () => {
    if (isLoading.value) return

    add5()
}

// A simple function for the click handler
const toggleVisibility = async () => {
    isVisible.value = !isVisible.value;

    if (isVisible.value) {
        // Reset the loading state and start fetching data again
       add5()
    }
    else {
        pgnListToRender.value = []
    }
    isLoading.value = false
};

onMounted(() => {
    isLoading.value = true
})
</script>


<style scoped>
#load-more {
    position: absolute;
    background: #aaa23a;
    color: black;
    border-radius: 50%;
    padding: 10px;
    z-index: 300;
    bottom: -20px;
    left: 50%;
    cursor: pointer;
}

.card-like {
    background-color: #1c1c1c;
    border: 1px solid #333;
    border-radius: 10px;
}

.event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    cursor: pointer;
    background-color: #232323;
    border-bottom: 1px solid #333;
    transition: background 0.2s;
}

.event-header:hover {
    background-color: #2f2f2f;
}

.event-body {
    padding: 12px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
}


.fade-highlight-enter-active {
    transition: background-color 1.5s ease;
}

.fade-highlight-enter-from {
    background-color: #444a2f;
    /* highlight color */
}

.fade-highlight-enter-to {
    background-color: transparent;
}

.highlight-container {
    border: 2px solid #aaa23a;
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 1rem;
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