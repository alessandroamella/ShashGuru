// stores/useChessStore.js
import { defineStore } from 'pinia'

export const useChessStore = defineStore('chess', {
  state: () => ({
    currentPGN: null,
  }),
  actions: {
    setPGN(pgn) {
      this.currentPGN = pgn
    },
  },
})
