import { defineStore } from 'pinia'

export const useChessStore = defineStore('chess', {
  state: () => ({
    currentPGN: null,
    selectedModel: null, // Holds the ID of the selected LLM
    selectedEvaluatorModel: null, // Holds the ID of the selected Evaluator LLM
  }),
  actions: {
    setPGN(pgn) {
      this.currentPGN = pgn
    },
    setSelectedModel(modelId) {
      this.selectedModel = modelId
    },
    setSelectedEvaluatorModel(modelId) {
      this.selectedEvaluatorModel = modelId
    }
  },
})
