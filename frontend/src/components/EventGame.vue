<template>
    <div id="eventGameCard" class="rounded m-3 p-2" style="">
        <!-- White Player -->
        <div id="whitePlayer" class="d-flex justify-content-between align-items-center">
            <div v-if="metadata.whitePlayerTitle" class="flex-shrink-0">
                <span  class="title ps-1">{{ metadata.whitePlayerTitle }}</span>
            </div>
            <div class="text-truncate px-1 flex-shrink-1">
                {{ metadata.whitePlayerName }}
            </div>
            <div v-if="metadata.whitePlayerRating" class="flex-item flex-grow-1 text-start">
                ({{ metadata.whitePlayerRating }})
            </div>
            <div v-if="resultFor('white')" class="flex-shrink-0">
                <span :class="['ms-3 pe-1 fw-bold fs-6', resultClass(resultFor('white'))]">
                    {{ resultFor('white') }}
                </span>
            </div>
        </div>

        <!-- Board -->
        <div class="position-relative d-flex justify-content-center" style="height:250px; width:250px;">
            <TheChessboard :board-config="boardConfig" style="height:250px; width:250px;" />

            <div v-if="metadata.gameResult === '*'" class="overlay d-flex justify-content-center align-items-center">
                Ongoing
            </div>
        </div>

        <!-- Black Player -->
        <div id="blackPlayer" class="d-flex justify-content-between align-items-center">
            <div v-if="metadata.blackPlayerTitle" class="flex-shrink-0">
                <span class="title ps-1">{{ metadata.blackPlayerTitle }}</span>
            </div>
            <div class="text-truncate px-1 flex-shrink-1">
                {{ metadata.blackPlayerName }}
            </div>
            <div v-if="metadata.blackPlayerRating" class="flex-item flex-grow-1 text-start">
                ({{ metadata.blackPlayerRating }})
            </div>
            <div v-if="resultFor('black')" class="flex-shrink-0">
                <span :class="['ms-3 pe-1 fw-bold fs-6', resultClass(resultFor('black'))]">
                    {{ resultFor('black') }}
                </span>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Chess } from 'chess.js';
import { TheChessboard } from 'vue3-chessboard';
import 'vue3-chessboard/style.css';

const props = defineProps({
    pgn: {
        type: String,
        default: ''
    }
})


const metadata = ref({})
const fen = ref('')
const boardConfig = ref({})

function extractMetadata(pgn) {
    const getTag = (tag) => {
        const regex = new RegExp(`\\[${tag} "(.*?)"\\]`);
        const match = pgn.match(regex);
        return match ? match[1] : null;
    };

    metadata.value = {
        whitePlayerTitle: getTag("WhiteTitle"),
        whitePlayerName: getTag("White"),
        whitePlayerRating: getTag("WhiteElo"),
        blackPlayerTitle: getTag("BlackTitle"),
        blackPlayerName: getTag("Black"),
        blackPlayerRating: getTag("BlackElo"),
        gameResult: getTag("Result"),
        openingName: getTag("Opening"),
    };
}

function pgnToFen(pgn) {
    const chess = new Chess();
    chess.loadPgn(pgn);
    return chess.fen(); // final position
}

function resultFor(side) {
    const res = metadata.value.gameResult;
    if (!res || res === '*') return null;
    if (res === '1-0') return side === 'white' ? '1' : '0';
    if (res === '0-1') return side === 'white' ? '0' : '1';
    if (res === '1/2-1/2') return '½';
    return null;
}

function resultClass(result) {
    if (result === '1') return 'text-victory ';
    if (result === '0') return 'text-danger ';
    return 'text-light ';
}


onMounted(() => {
    if (props.pgn) {
        fen.value = pgnToFen(props.pgn);
        boardConfig.value = {
            fen: fen,
            viewOnly: true,
        }
        console.log('Board config:', boardConfig);
        extractMetadata(props.pgn)
    }
})

</script>

<style scoped>
#eventGameCard {
    width: 270px;
    color: #ddd;
    background-color: #262421;
    border: 1px solid #262421;
    transition: 0.3s;
}

#eventGameCard:hover {
    background-color: #2c2a27;
    border: 1px solid #aaa23a;
}

.title {
    color: #aaa23a;
    font-weight: bold;
}

.overlay {
    position: absolute;
    top: 0;
    left: 0;
    height: inherit;
    width: inherit;
    background-color: rgba(0, 0, 0, 0.4);
    color: white;
    font-weight: bold;
    font-size: 2rem;
    z-index: 100;
    cursor: not-allowed
}
.text-victory {
    color: #629924;
}
.text-loss {
    color: #cc3333;
}
</style>