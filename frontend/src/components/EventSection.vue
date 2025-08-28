<template>
    <div v-if="shouldRender" class="card-like event-section mx-5 mb-3">
        <!-- Header -->
        <div class="d-flex flex-row align-items-start p-3 cursor-pointer event-header" @click="isVisible = !isVisible">
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
                <EventGame v-for="(pgn) in pgnList" 
                    :key="pgn.index" 
                    :pgn="pgn" 
                    class="flex-item shadow"
                />
            </div>
        </transition>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import EventGame from './EventGame.vue'

const props = defineProps({
    title: { type: String, required: true },
    pgnList: { type: Array, default: () => [] },
    shouldRender: { type: Boolean, default: true },
    initiallyOpen: { type: Boolean, default: false }
})
const isVisible = ref(props.initiallyOpen)


</script>


<style scoped>
.card-like {
    background-color: #1c1c1c;
    border: 1px solid #333;
    border-radius: 10px;
    overflow: hidden;
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