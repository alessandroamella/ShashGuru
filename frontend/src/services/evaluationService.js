import axios from 'axios'

export class EvaluationService {
  static async fetchEvaluation(fen, depth = 15, lines = 1) {
    if (!fen) {
      return null
    }
    
    try {
      // Determine whose turn it is from the FEN
      const fenParts = fen.split(' ')
      const isWhiteToMove = fenParts[1] === 'w'
      
      const server_url = import.meta.env.BASE_URL + 'backend'
      const response = await axios.post(`${server_url}/evaluation`, {
        fen: fen,
        depth: depth,
        lines: lines
      })
      
      if (response.data && response.data.evaluation) {
        // Store both the evaluation and the side info for proper interpretation
        return {
          ...response.data.evaluation,
          sideToMove: isWhiteToMove ? 'white' : 'black'
        }
      }
    } catch (error) {
      console.error('Error fetching evaluation:', error)
      throw error
    }
    
    return null
  }
}
