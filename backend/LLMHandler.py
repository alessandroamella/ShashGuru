# This file is part of ShashGuru, a chess analyzer that takes a FEN, asks a UCI chess engine to analyse it and then outputs a natural language analysis made by an LLM.
# Copyright (C) 2025  Alessandro Libralesso
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from openai import OpenAI
from google import genai
from google.genai import types
import logging as log
import warnings
import math

# Import for prompt creation
from fenManipulation import fen_explainer
import chess
import os

# Import rate limiter for Google API
from google_rate_limiter import GoogleRateLimiter, RateLimitExceeded

# Default configuration
DEFAULT_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "llama-3.1-8b-instant")
DEFAULT_LLM_API_KEY = os.environ.get("DEFAULT_LLM_API_KEY", "unused")

# Initialize Google rate limiter
google_rate_limiter = GoogleRateLimiter()

# Provider-specific configuration
MODEL_PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
    },
    # Google models now use native Gemini SDK (not OpenAI compatibility)
    "google": {
        "base_url": None,  # Not used - native SDK
        "api_key_env": "GOOGLE_API_KEY",
    },
}

# Supported models list - You can expand this
SUPPORTED_MODELS = [
    {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B (Groq)",
        "provider": "groq",
    },
    {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B (Groq)",
        "provider": "groq",
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "provider": "google",
    },
    {
        "id": "gemini-3-flash-preview",
        "name": "Gemini 3 Flash",
        "provider": "google",
    },
    {"id": "gemini-3-pro-preview", "name": "Gemini 3 Pro", "provider": "google"},
]

# Log warning if API key is not set
if (
    DEFAULT_LLM_API_KEY == "unused"
    and os.environ.get("USE_CLOUD_AI", "false").lower() == "false"
):
    log.warning("DEFAULT_LLM_API_KEY is not set.")


SYSTEM_MESSAGES = {
    "default": """
You are a concise chess analysis assistant. For initial position analysis, provide brief, accurate insights based only on the given information.
Focus on the most important aspects: the recommended move and its purpose.
Keep responses short (2-3 sentences max). Avoid speculation or moves not mentioned in the analysis.
Use clear, natural chess language without unnecessary elaboration.
Keep the tone encouraging and educational.

For follow-up questions, refer back to the position and engine analysis provided in the conversation context.
Maintain the same brevity and focus on concrete information when answering follow-ups.

If asked about moves that were not analyzed by the engine, respond that you don't have analysis for those moves and suggest the user try those moves on the board and re-run the analysis to get engine evaluation for them.
""",
    "grandmaster": """
You are a distinguished grandmaster providing professional chess analysis. Draw from deep strategic understanding and classical chess principles.
Analyze positions with the precision and depth of a world-class player. Reference opening principles, middlegame strategy, and endgame technique as appropriate.
Use sophisticated chess terminology and explain the deeper strategic concepts behind moves.
Provide insights that would be valuable to serious competitive players, focusing on long-term positional factors and tactical nuances.
Keep responses focused and concise - avoid lengthy explanations. 3-4 sentences maximum.

For follow-up questions, maintain the same authoritative and educational tone, always grounding responses in sound chess theory while staying brief.
""",
}

# Keep backward compatibility
SYSTEM_MESSAGE = SYSTEM_MESSAGES["default"]

# Style labels mapping
STYLE_LABELS = {
    "default": "Commentator",
    "grandmaster": "Grandmaster",
}


def get_analysis_styles():
    """
    Returns the available analysis styles with their labels.
    Derives from SYSTEM_MESSAGES to maintain consistency.
    """
    return [
        {"value": style_key, "label": STYLE_LABELS.get(style_key, style_key.title())}
        for style_key in SYSTEM_MESSAGES.keys()
    ]


def get_available_models():
    """Returns the list of supported models."""
    return SUPPORTED_MODELS


def is_gemini_model(model_name):
    """
    Check if the given model name is a Gemini model that should use the native SDK.

    Args:
        model_name: The model ID to check

    Returns:
        bool: True if it's a Gemini model
    """
    if not model_name:
        return False
    return "gemini" in model_name.lower()


def get_gemini_client(model_name=None):
    """
    Initialize and return a Gemini client using the native Google SDK.

    Args:
        model_name: The model ID (not used for client init, but kept for consistency)

    Returns:
        genai.Client: Initialized Gemini client
    """
    api_key = os.environ.get("GOOGLE_API_KEY", "unused")
    if api_key == "unused":
        log.warning("GOOGLE_API_KEY not set for Gemini models")

    # The genai.Client() will automatically use GOOGLE_API_KEY from environment
    client = genai.Client(api_key=api_key)
    log.info(f"Initialized Gemini client for model {model_name or 'default'}")
    return client


def get_model_config(model_name=None):
    """
    Get the configuration (base_url, api_key) for a specific model.
    Falls back to environment variable DEFAULT_AI_BASE_URL if set (for local models).

    Args:
        model_name: The model ID to get config for. If None, uses DEFAULT_MODEL.

    Returns:
        tuple: (base_url, api_key)
    """
    if model_name is None:
        log.warning(f"No model_name provided, using DEFAULT_MODEL: {DEFAULT_MODEL}")
        model_name = DEFAULT_MODEL

    # Check if DEFAULT_AI_BASE_URL is set (for local/custom endpoints)
    env_base_url = os.environ.get("DEFAULT_AI_BASE_URL")
    if env_base_url:
        log.info(f"Using custom AI base URL: {env_base_url}")
        return env_base_url, DEFAULT_LLM_API_KEY

    # Find the provider for this model
    provider = None
    for model in SUPPORTED_MODELS:
        if model["id"] == model_name:
            provider = model["provider"]
            break

    if provider is None:
        log.warning(
            f"Model {model_name} not found in SUPPORTED_MODELS, using default provider (groq)"
        )
        provider = "groq"

    # Get provider config
    provider_config = MODEL_PROVIDERS.get(provider)
    if provider_config is None:
        raise ValueError(f"Provider {provider} not configured in MODEL_PROVIDERS")

    # Get API key from environment
    api_key = os.environ.get(provider_config["api_key_env"], "unused")
    if api_key == "unused":
        log.warning(
            f"API key not set for provider {provider} (expected env var: {provider_config['api_key_env']})"
        )

    return provider_config["base_url"], api_key


def load_LLM_model(model_name=None):
    """
    Initialize the OpenAI client with the correct base URL and API key for the specified model.

    Args:
        model_name: The model ID to configure for. If None, uses DEFAULT_MODEL.

    Returns:
        tuple: (None, OpenAI client instance)
    """
    # Removing logging
    # transformers.utils.logging.disable_progress_bar()
    warnings.filterwarnings("ignore")

    base_url, api_key = get_model_config(model_name)

    log.info(
        f"Initializing LLM client for model {model_name or DEFAULT_MODEL} with base_url: {base_url}"
    )
    model = OpenAI(base_url=base_url, api_key=api_key)
    return None, model


def __format_eval(entry):

    if "mate" in entry and entry["mate"] is not None:
        return f"mate in {entry['mate']}"
    elif "score" in entry:
        return f"{entry['score']} cp"
    return None


def __mapWinProb(winprob, side, score=None, mate=None):
    # FALLBACK: If engine didn't give winprob, calculate it from score/mate
    if winprob is None:
        if mate is not None:
            # If mate is found: Positive mate = 100% win, Negative = 0%
            winprob = 100 if mate > 0 else 0
        elif score is not None:
            # Convert Centipawns to Win Probability (Sigmoid curve approximation)
            # +100 cp is roughly 60% win chance
            try:
                winprob = 50 + 50 * (2 / (1 + math.exp(-0.00368 * score)) - 1)
            except OverflowError:
                winprob = 100 if score > 0 else 0
        else:
            return "Unclear position."

    # Ensure winprob is an integer for comparison
    winprob = int(winprob)

    if 0 <= winprob <= 5:
        return f"{side} has a decisive disadvantage, with the position clearly leading to a loss."
    elif 6 <= winprob <= 10:
        return f"{side} has decisive disadvantage: the opponent has a dominant position and is likely winning."
    elif 11 <= winprob <= 15:
        return f"{side} has clear disadvantage: a substantial positional disadvantage, but a win is not yet inevitable."
    elif 16 <= winprob <= 20:
        return f"{side} has a significant disadvantage: difficult to recover."
    elif 21 <= winprob <= 24:
        return f"{side} has a slight disadvantage with a positional edge, but no immediate threats."
    elif 25 <= winprob <= 49:
        return f"{side} is in a defensive position. The opponent has an initiative."
    elif winprob == 50:
        return "The position is equal. Both sides are evenly matched, with no evident advantage."
    elif 51 <= winprob <= 75:
        return f"{side} has initiative: by applying pressure and it can achieve an edge with active moves and forcing ideas."
    elif 76 <= winprob <= 79:
        return f"{side} has a slight advantage: a minor positional edge, but it’s not decisive."
    elif 80 <= winprob <= 84:
        return f"{side} is slightly better, tending toward a clear advantage. The advantage is growing, but the position is still not decisive."
    elif 85 <= winprob <= 89:
        return f"{side} has a clear advantage: a significant edge, but still with defensive chances."
    elif 90 <= winprob <= 94:
        return f"{side} has a dominant position, almost decisive, not quite winning yet, but trending toward victory."
    elif 95 <= winprob <= 100:
        return f"{side} has a decisive advantage, with victory nearly assured."
    else:
        return "Total chaos: unclear position, dynamically balanced."


def generate_line(line, board):
    tmp_board = board.copy()
    san_line = []
    for idx, move in enumerate(line):
        uci_move = chess.Move.from_uci(move)
        san_move = tmp_board.san(uci_move)
        if idx > 0:
            # Skip the first move
            san_line.append(san_move)
        tmp_board.push(uci_move)
    return " ".join(san_line)


def analyze_position_context(fen, board):
    """Generate additional context about the position for the LLM"""
    context = []

    # Material count
    material = {
        chess.PAWN: 1,
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
        chess.KING: 0,
    }

    white_material = sum(
        material[piece.piece_type]
        for piece in board.piece_map().values()
        if piece.color == chess.WHITE
    )
    black_material = sum(
        material[piece.piece_type]
        for piece in board.piece_map().values()
        if piece.color == chess.BLACK
    )

    material_diff = white_material - black_material
    if material_diff > 0:
        context.append(f"Material: White is ahead by {material_diff} points")
    elif material_diff < 0:
        context.append(f"Material: Black is ahead by {abs(material_diff)} points")
    else:
        context.append("Material: Equal material")

    # King safety
    white_king_square = board.king(chess.WHITE)
    black_king_square = board.king(chess.BLACK)

    if white_king_square:
        white_king_file = chess.square_file(white_king_square)
        white_king_rank = chess.square_rank(white_king_square)
        if white_king_rank <= 1 and (white_king_file <= 2 or white_king_file >= 5):
            context.append("White king appears castled/safe")
        elif white_king_rank >= 3:
            context.append("White king is exposed in the center")

    if black_king_square:
        black_king_file = chess.square_file(black_king_square)
        black_king_rank = chess.square_rank(black_king_square)
        if black_king_rank >= 6 and (black_king_file <= 2 or black_king_file >= 5):
            context.append("Black king appears castled/safe")
        elif black_king_rank <= 4:
            context.append("Black king is exposed in the center")

    # Check status
    if board.is_check():
        context.append(
            f"{'White' if board.turn == chess.WHITE else 'Black'} king is in check"
        )

    # Game phase indicator
    total_pieces = len(board.piece_map())
    if total_pieces > 24:
        context.append("Position: Opening/Early middlegame")
    elif total_pieces > 12:
        context.append("Position: Middlegame")
    else:
        context.append("Position: Endgame")

    # Castling Rights
    w_rights = []
    if board.has_kingside_castling_rights(chess.WHITE):
        w_rights.append("Kingside")
    if board.has_queenside_castling_rights(chess.WHITE):
        w_rights.append("Queenside")
    if w_rights:
        context.append(f"White castling rights: {'/'.join(w_rights)}")

    b_rights = []
    if board.has_kingside_castling_rights(chess.BLACK):
        b_rights.append("Kingside")
    if board.has_queenside_castling_rights(chess.BLACK):
        b_rights.append("Queenside")
    if b_rights:
        context.append(f"Black castling rights: {'/'.join(b_rights)}")

    # Center Occupation
    center_sqs = [chess.E4, chess.D4, chess.E5, chess.D5]
    w_center = sum(
        1
        for sq in center_sqs
        if board.piece_at(sq) and board.piece_at(sq).color == chess.WHITE
    )
    b_center = sum(
        1
        for sq in center_sqs
        if board.piece_at(sq) and board.piece_at(sq).color == chess.BLACK
    )
    if w_center > b_center:
        context.append("White occupies more center squares")
    elif b_center > w_center:
        context.append("Black occupies more center squares")

    return "; ".join(context)


def analysis_to_string(fen, side, analysis):
    output = []
    board = chess.Board(fen)

    # Show top 3 moves with their evaluations
    for idx, item in enumerate(analysis[:3]):
        eval_text = __mapWinProb(item["winprob"], side)
        line_moves = generate_line(item["pv_moves"][:5], board)

        # Add move explanation
        first_move = item["pv_moves"][0] if item["pv_moves"] else "No move"
        move_obj = chess.Move.from_uci(first_move)
        move_san = board.san(move_obj)

        output.append(f"Option {idx+1}: {move_san} - {eval_text}")
        if line_moves:
            output.append(f"   Continuation: {line_moves}")

    return "\n".join(output)


def create_prompt_single_engine(fen, bestmoves, ponder, style="default"):
    log.basicConfig(level=log.INFO)
    explainedFEN, side = fen_explainer(fen)
    board = chess.Board(fen)

    # NEW: Check for game over conditions before checking engine analysis
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        prompt = f"{explainedFEN}\n\nThe game is over. {winner} has won by checkmate. Explain the final position and the checkmate pattern."
        if style == "grandmaster":
            prompt = f"The game has concluded with {winner} delivering checkmate. {explainedFEN}\n\nAs a Grandmaster, analyze the final mating pattern and the decisive elements of the position."
        return prompt

    if board.is_stalemate():
        prompt = f"{explainedFEN}\n\nThe game is drawn by stalemate. Explain why the king has no legal moves but is not in check."
        if style == "grandmaster":
            prompt = f"The game has ended in a stalemate. {explainedFEN}\n\nAs a Grandmaster, comment on this draw resource."
        return prompt

    if board.is_insufficient_material():
        prompt = f"{explainedFEN}\n\nThe game is drawn due to insufficient material."
        return prompt

    if board.is_game_over():  # Catch-all for other draws (repetition, 50-move)
        result = board.result()
        prompt = f"{explainedFEN}\n\nThe game has ended. Result: {result}. Explain the situation."
        return prompt

    # Get position context
    position_context = analyze_position_context(fen, board)

    # Generate analysis for top 3 moves
    moves_analysis = []
    for idx, move_data in enumerate(bestmoves[:3]):
        if not move_data or not move_data.get("pv_moves"):
            continue

        move_uci = move_data["pv_moves"][0]
        move_san = board.san(chess.Move.from_uci(move_uci))
        win_prob_text = __mapWinProb(
            move_data.get("winprob"),
            side,
            score=move_data.get("score"),
            mate=move_data.get("mate"),
        )
        continuation = generate_line(move_data["pv_moves"][:4], board)

        moves_analysis.append(
            {
                "rank": idx + 1,
                "move_san": move_san,
                "move_uci": move_uci,
                "evaluation": win_prob_text,
                "continuation": continuation,
            }
        )

    # Create style-specific prompts
    if style == "grandmaster":
        prompt = create_grandmaster_prompt(
            explainedFEN, side, position_context, moves_analysis
        )
    else:  # default/commentator
        prompt = create_default_prompt(
            explainedFEN, side, position_context, moves_analysis
        )

    log.info(f"Generated {style} prompt for single engine:")
    log.info(prompt)
    return prompt


def create_default_prompt(explainedFEN, side, position_context, moves_analysis):
    if not moves_analysis:
        return f"{explainedFEN}\n\nThe engine failed to analyze this position. Please ask me to analyze it again or check the logs."

    best_move = moves_analysis[0]

    prompt = f"""Position Context:
{explainedFEN}
{position_context}

Engine Analysis:
Recommended Move: {best_move['move_san']}
Continuation: {best_move['continuation']}
Evaluation: {best_move['evaluation']}

Task:
Explain why {best_move['move_san']} is the best move.
1. Identify the immediate tactical or strategic reason for the move.
2. Explain how it improves {side}'s position or prevents a threat.
3. Mention the long-term plan implied by this move.

Keep the explanation concise (approx. 3-4 sentences) and accessible to an intermediate player."""

    return prompt


def create_grandmaster_prompt(explainedFEN, side, position_context, moves_analysis):
    if not moves_analysis:
        return "The engine could not analyze this position. As a Grandmaster, I cannot comment on specific lines without calculation."

    moves_text = "\n".join(
        [
            f"{move['rank']}. {move['move_san']} - {move['evaluation']} (continuation: {move['continuation']})"
            for move in moves_analysis
        ]
    )

    prompt = f"""Position Context:
{explainedFEN}
{position_context}
Side to move: {side}

Engine Analysis - Top Candidate Moves:
{moves_text}

Task:
As a Grandmaster, provide a professional analysis of this position.
1. Evaluate the strategic merits of the top recommendation.
2. Discuss the alternative options and why they might be inferior or different.
3. Explain the underlying chess principles (tactical and positional) that make these moves strong.

Maintain a sophisticated, educational tone suitable for a serious player."""

    return prompt


def create_prompt_double_engine(fen, engine_analysis):
    explainedFEN = fen_explainer(fen)

    nnue = engine_analysis["NNUE"]
    human = engine_analysis["HUMAN"]

    nnue_best = nnue["top_moves"][0]["move"]
    human_best = human["top_moves"][0]["move"]

    nnue_best_eval = __format_eval(nnue["top_moves"][0])
    human_best_eval = __format_eval(human["top_moves"][0])

    bestmove_prompt = f"""I have two engines: one with NNUE, called ShashChess, and another that simulates human thought, called Alexander.
        ShashChess suggests the best move **{nnue_best}** (in UCI format) {f"with an evaluation of {nnue_best_eval}" if nnue_best_eval is not None else "" },
        while Alexander suggests the best move is **{human_best}** (in UCI format) {f"with an evaluation of {human_best_eval}" if human_best_eval is not None else "" }.
        ShashChess evaluates Alexander's top move with a score of {nnue['eval_human_move']} and Alexander evaluates ShashChess' best move with a score of {human['eval_nnue_move']}.
        If the engines disagree on the best move, note that ShashChess also suggests these other strong moves: {nnue['top_moves'][1:]},
        while Alexander suggests these: {human['top_moves'][1:]}.
        If either engine considers the other's top choice among these alternatives, that might imply partial agreement."""

    counter_prompt = f"""{"ShashChess expects a reply to his best move of **" + engine_analysis['NNUE'].get('ponder', '') + "**." if engine_analysis['NNUE'].get('ponder') else ""}
        {"Alexander expects a reply to his best move of **" + engine_analysis['HUMAN'].get('ponder', '') + "**." if engine_analysis['HUMAN'].get('ponder') else ""}
        {"ShashChess also evaluates Alexander's expected reply with a score of " + str(nnue['eval_human_ponder']) + "." if nnue['eval_human_ponder'] is not None else ""}
        {"Alexander also evaluates ShashChess's expected reply with a score of " + str(human['eval_nnue_ponder']) + "." if human['eval_nnue_ponder'] is not None else ""}"""

    full_prompt = (
        "I will explain the board situation:\n"
        + explainedFEN
        + "\n\n"
        + bestmove_prompt
        + " "
        + counter_prompt
        + "Can you explain why these suggested moves are strong? Provide an insightful chess analysis."
    )
    return full_prompt


def _get_request_kwargs(model_name):
    """
    Prepare extra arguments for specific models (e.g. Gemini Thinking).
    """
    kwargs = {
        "model": model_name if model_name else DEFAULT_MODEL,
    }

    return kwargs


def query_LLM(
    prompt,
    tokenizer,
    model,
    chat_history=None,
    max_history=10,
    style="default",
    model_name=None,
):
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]

    system_message = SYSTEM_MESSAGES.get(style, SYSTEM_MESSAGES["default"])

    # Check if this is a Gemini model - use native SDK
    if is_gemini_model(model_name):
        # Check rate limit before making the call
        if not google_rate_limiter.can_make_call():
            stats = google_rate_limiter.get_usage_stats()
            raise RateLimitExceeded(stats)

        client = get_gemini_client(model_name)

        # Convert chat history to Gemini format
        # Gemini uses 'contents' with 'parts' structure
        contents = []
        for msg in chat_history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Add current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        gen_config_params = {"system_instruction": system_message}

        # Disable thinking for Gemini 2.x or models that don't support it
        # You can adjust this condition based on specific model capabilities
        if model_name and "gemini-2" not in model_name:
            gen_config_params["thinking_config"] = types.ThinkingConfig(
                thinking_level="high"
            )

        config = types.GenerateContentConfig(**gen_config_params)

        response = client.models.generate_content(
            model=model_name or DEFAULT_MODEL, contents=contents, config=config
        )

        # Increment call counter after successful call
        google_rate_limiter.increment_call()

        analysis = response.text
    else:
        # Use OpenAI-compatible client for non-Gemini models
        _, client = load_LLM_model(model_name)

        messages = (
            [{"role": "system", "content": system_message}]
            + chat_history
            + [{"role": "user", "content": prompt}]
        )

        request_kwargs = _get_request_kwargs(model_name)

        response = client.chat.completions.create(
            messages=messages, max_completion_tokens=1024, **request_kwargs
        )

        analysis = response.choices[0].message.content

    # Update chat history
    chat_history.append({"role": "user", "content": prompt})
    chat_history.append({"role": "assistant", "content": analysis})

    return analysis, chat_history


def stream_LLM(
    prompt, model, chat_history=None, max_history=10, style="default", model_name=None
):
    if chat_history is None:
        chat_history = []
    chat_history = chat_history[-max_history:]

    system_message = SYSTEM_MESSAGES.get(style, SYSTEM_MESSAGES["default"])

    # Check if this is a Gemini model - use native SDK
    if is_gemini_model(model_name):
        # Check rate limit before making the call
        if not google_rate_limiter.can_make_call():
            stats = google_rate_limiter.get_usage_stats()
            raise RateLimitExceeded(stats)

        client = get_gemini_client(model_name)

        # Convert chat history to Gemini format
        contents = []
        for msg in chat_history:
            role = "model" if msg["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        # Add current prompt
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        gen_config_params = {"system_instruction": system_message}

        # Disable thinking for Gemini 2.x
        if model_name and "gemini-2" not in model_name:
            gen_config_params["thinking_config"] = types.ThinkingConfig(
                thinking_level="high", include_thoughts=True
            )

        config = types.GenerateContentConfig(**gen_config_params)

        # Use streaming API
        response_stream = client.models.generate_content_stream(
            model=model_name or DEFAULT_MODEL, contents=contents, config=config
        )

        # Increment call counter after initiating the stream
        google_rate_limiter.increment_call()

        thought_mode = False  # Track if we are currently inside a thought block

        for chunk in response_stream:
            # Gemini chunks can contain multiple parts (thoughts or text)
            if not chunk.candidates or not chunk.candidates[0].content.parts:
                continue

            for part in chunk.candidates[0].content.parts:
                # 1. Handle Thought Parts
                if part.thought:
                    # If we weren't in thought mode, open the tag
                    if not thought_mode:
                        yield "<think>"
                        thought_mode = True

                    yield part.text

                # 2. Handle Answer Parts (part.thought is False, but text exists)
                elif part.text:
                    # If we were in thought mode, we must close it now
                    if thought_mode:
                        yield "</think>"
                        thought_mode = False

                    yield part.text

        # Safety: Check if we finished the stream while still inside a thought
        if thought_mode:
            yield "</think>"
    else:
        # Use OpenAI-compatible client for non-Gemini models
        _, client = load_LLM_model(model_name)

        messages = (
            [{"role": "system", "content": system_message}]
            + chat_history
            + [{"role": "user", "content": prompt}]
        )

        request_kwargs = _get_request_kwargs(model_name)

        # Add stream specific params
        request_kwargs["stream"] = True
        request_kwargs["max_completion_tokens"] = (
            4096  # Higher limit for thinking models
        )

        output = client.chat.completions.create(messages=messages, **request_kwargs)

        for out in output:
            if out.choices[0].finish_reason is not None:
                break

            # Standard content
            delta = out.choices[0].delta.content
            if delta:
                yield delta


def is_chess_related(question, tokenizer, model, model_name=None):
    system_message = """You are a filtering agent.
Your job is to decide if the text is chess-related.
Keep context in mind.
Only answer with a "yes" or a "no".
"""
    user_message = question + "Is this question chess-related?"

    # Check if this is a Gemini model - use native SDK
    if is_gemini_model(model_name):
        # Check rate limit before making the call
        if not google_rate_limiter.can_make_call():
            stats = google_rate_limiter.get_usage_stats()
            raise RateLimitExceeded(stats)

        client = get_gemini_client(model_name)

        config = types.GenerateContentConfig(
            system_instruction=system_message,
            thinking_config=types.ThinkingConfig(
                thinking_level="minimal"  # Fast filtering
            ),
        )

        response = client.models.generate_content(
            model=model_name or DEFAULT_MODEL, contents=user_message, config=config
        )

        # Increment call counter after successful call
        google_rate_limiter.increment_call()

        response_text = response.text.strip().lower()
    else:
        # Use OpenAI-compatible client for non-Gemini models
        _, client = load_LLM_model(model_name)

        messages = [
            {
                "role": "system",
                "content": system_message,
            },
            {"role": "user", "content": user_message},
        ]

        request_kwargs = _get_request_kwargs(model_name)

        output = client.chat.completions.create(
            messages=messages, max_completion_tokens=256, **request_kwargs
        )

        response_text = output.choices[0].message.content.strip().lower()

    return response_text in ["yes", "yes."]
