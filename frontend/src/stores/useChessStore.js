import { defineStore } from 'pinia'

export const useChessStore = defineStore('chess', {
  state: () => ({
    currentPGN: null,
    selectedModel: null, // Holds the ID of the selected LLM
  }),
  actions: {
    setPGN(pgn) {
      this.currentPGN = pgn
    },
    setSelectedModel(modelId) {
      this.selectedModel = modelId
    }
  },
})
