import socket
import threading
import random
import json
import time
import sys

# Configuração dos endereços e portas de cada máquina
nodes = [
    ('127.0.0.1', 5000),
    ('127.0.0.1', 5001),
    ('127.0.0.1', 5002),
    ('127.0.0.1', 5003)
]

# Índice do nó atual (mudar conforme necessário)
current_node_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# Contador de rodadas
current_round = 1

# Socket DGRAM (UDP)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(nodes[current_node_index])

# Função para enviar mensagens
def send_message(message, target_node_index):
    sock.sendto(message.encode(), nodes[target_node_index])

# Função para receber mensagens
def receive_message():
    while True:
        data, addr = sock.recvfrom(1024)
        handle_message(data.decode())

# Thread para receber mensagens
threading.Thread(target=receive_message, daemon=True).start()

# Função para enviar o bastão para o próximo nó
def pass_token():
    next_node_index = (current_node_index + 1) % len(nodes)
    send_message("TOKEN", next_node_index)

# Função para lidar com mensagens recebidas
def handle_message(message):
    if message == "TOKEN":
        start_round()
    else:
        process_game_message(json.loads(message))

# Função para iniciar uma rodada
def start_round():
    if is_dealer():
        distribute_cards()
        start_betting()
    else:
        pass_token()

# Função para verificar se o nó atual é o dealer
def is_dealer():
    return current_node_index == 0

# Função para distribuir cartas
def distribute_cards():
    global current_round
    suits = ['♦', '♠', '♥', '♣']
    ranks = ['4', '5', '6', '7', 'Q', 'J', 'K', 'A', '2', '3']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    cards_per_player = 14 - current_round  # Diminui a quantidade de cartas a cada rodada
    hands = {i: deck[i*cards_per_player:(i+1)*cards_per_player] for i in range(len(nodes))}
    for i, hand in hands.items():
        send_message(json.dumps({'type': 'CARDS', 'hand': hand}), i)
    current_round += 1

# Função para iniciar as apostas
def start_betting():
    if current_node_index == 0:
        bet = get_player_bet()
        send_message(json.dumps({'type': 'BET', 'player': current_node_index, 'bet': bet}), current_node_index)
    else:
        pass_token()

# Função para obter a aposta do jogador
def get_player_bet():
    max_bet = 14 - current_round
    while True:
        try:
            bet = int(input(f"Digite sua aposta (0 a {max_bet}): "))
            if 0 <= bet <= max_bet:
                return bet
            else:
                print(f"Aposta inválida. Digite um número entre 0 e {max_bet}.")
        except ValueError:
            print("Entrada inválida. Por favor, digite um número.")

# Função para processar mensagens de jogo
def process_game_message(message):
    if message['type'] == 'CARDS':
        handle_cards(message['hand'])
    elif message['type'] == 'BET':
        handle_bet(message['player'], message['bet'])
    elif message['type'] == 'PLAY':
        handle_play(message['cards_played'])
    elif message['type'] == 'RESULT':
        handle_result(message['results'])
    elif message['type'] == 'SCORE':
        handle_score(message['scores'])

# Função para lidar com cartas recebidas
def handle_cards(hand):
    global player_hand
    player_hand = hand
    print(f"Received cards: {hand}")

# Função para lidar com apostas
def handle_bet(player, bet):
    global bets, player_bets
    player_bets[player] = bet
    bets[player] = bet
    if len(bets) == len(nodes):
        start_game()
    else:
        pass_token()

# Função para iniciar o jogo após as apostas
def start_game():
    send_message(json.dumps({'type': 'PLAY', 'cards_played': []}), current_node_index)

# Função para lidar com jogadas
def handle_play(cards_played):
    global current_round, current_player, player_wins

    if len(cards_played) < (14 - current_round):
        card_to_play = get_player_card()
        cards_played.append(card_to_play)
        next_node_index = (current_node_index + 1) % len(nodes)
        send_message(json.dumps({'type': 'PLAY', 'cards_played': cards_played}), next_node_index)
    else:
        calculate_results(cards_played)

# Função para obter a carta do jogador
def get_player_card():
    while True:
        print(f"Sua mão: {player_hand}")
        card = input("Escolha uma carta para jogar: ")
        if card in player_hand:
            player_hand.remove(card)
            return card
        else:
            print("Carta inválida. Escolha uma carta da sua mão.")

# Função para calcular resultados
def calculate_results(cards_played):
    results = {player: 0 for player in range(len(nodes))}
    winning_card = max(cards_played)
    winners = [i for i, card in enumerate(cards_played) if card == winning_card]
    
    if len(winners) == len(cards_played):
        print("Empate! Todos jogaram a mesma carta.")
    else:
        for winner in winners:
            results[winner] += 1
    
    send_message(json.dumps({'type': 'RESULT', 'results': results}), current_node_index)

# Função para lidar com resultados
def handle_result(results):
    global player_scores, player_bets
    for player, wins in results.items():
        difference = abs(player_bets[player] - wins)
        player_scores[player] -= difference
    update_scores_and_pass_token()

# Função para lidar com pontuações
def handle_score(scores):
    global player_scores
    player_scores = scores
    print(f"Updated scores: {player_scores}")
    check_for_elimination()

# Função para verificar se algum jogador foi eliminado
def check_for_elimination():
    global player_scores, nodes
    for player, score in list(player_scores.items()):
        if score <= 0:
            print(f"Player {player} has been eliminated!")
            del player_scores[player]
            nodes.remove(nodes[player])
    pass_token()

# Função para atualizar pontuações e passar o bastão
def update_scores_and_pass_token():
    for i in range(len(nodes)):
        send_message(json.dumps({'type': 'SCORE', 'scores': player_scores}), i)
    pass_token()

# Iniciar o processo de jogo
if __name__ == "__main__":
    player_hand = []
    bets = {}
    player_scores = {i: 12 for i in range(len(nodes))}
    player_bets = {}
    player_wins = {i: 0 for i in range(len(nodes))}
    pass_token() if is_dealer() else receive_message()
    while True:
        time.sleep(1)
        pass