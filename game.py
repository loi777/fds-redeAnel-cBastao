import socket
import threading
import random
import json
import time
import sys
import signal

# Configuração dos endereços e portas de cada máquina
nodes = [
    ('127.0.0.1', 5000),
    ('127.0.0.1', 5001),
    ('127.0.0.1', 5002),
    ('127.0.0.1', 5003)
]

# Índice do nó atual (mudar conforme necessário)
current_node_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0

# Variáveis globais
current_round = 11 #iniciar com 1
player_hand = []
bets = {}
player_scores = [12, 12, 12, 12] #i: 12 for i in range(len(nodes))
players_wins = {}
cards_played = {}
results = [0, 0, 0, 0]     #{i: 0 for i in range(len(nodes))}
player_wins = [0, 0, 0, 0]     #{i: 0 for i in range(len(nodes))}
dealer_index = 0  # Dealer inicial
token = False  # Variável para indicar se o nó atual possui o token

# Socket DGRAM (UDP)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(nodes[current_node_index])

# Função para enviar mensagens
def send_message(message, target_node_index):
    target_node = nodes[target_node_index]
    sock.sendto(message.encode(), target_node)
    print(f"Enviando mensagem para {target_node}: {message}")

# Função para receber mensagens
def receive_message():
    while True:
        message, address = sock.recvfrom(1024)
        message = message.decode()
        print(f"Mensagem recebida de {address}: {message}")
        handle_message(message)

# Thread para receber mensagens
threading.Thread(target=receive_message, daemon=True).start()

# Função para enviar o bastão para o próximo nó
def pass_token(next_node_index):
    global token
    send_message("TOKEN", next_node_index)
    print(f"Passando o bastão para o próximo nó: {next_node_index}")
    token = False

# Função para lidar com mensagens recebidas, só deve inicializar o jogo uma vez no início do current_round
def handle_message(message):
    global token
    if message == "TOKEN":
        print("Recebido TOKEN")
        token = True
    else:
        process_game_message(json.loads(message))

# Função para processar mensagens de jogo
def process_game_message(message):
    message_type = message.get('type')
    if message_type == 'START':
        handle_start(message.get('dealer'))
    elif message_type == 'CARDS':
        handle_cards(message.get('hand'))
    elif message_type == 'BET':
        handle_bet(message.get('player'), message.get('bet'))
    elif message_type == 'PLAY':
        handle_play(message.get('player'), message.get('card'))
    elif message_type == 'RESULT':
        handle_result(message.get('results'))
    elif message_type == 'SCORE':
        handle_score(message.get('scores'))
    else:
        print("Mensagem inválida")

    #message_type = message.get('type')
    #if message_type == 'START':
    #    handle_start(message['dealer'])
    #elif message_type == 'CARDS':
    #    handle_cards(message['hand'])
    #elif message_type == 'BET':
    #    handle_bet(message['player'], message['bet'])
    #elif message_type == 'PLAY':
    #    handle_play(message['player'], message['card'])
    #elif message_type == 'RESULT':
    #    handle_result(message['results'])
    #elif message_type == 'SCORE':
    #    handle_score(message['scores'])
    #else:
    #    print(f"Mensagem inválida: {message}")

# Função para lidar com o início do jogo
def handle_start(dealer):
    global dealer_index
    dealer_index = dealer
    print(f"Iniciando jogo com dealer {dealer}")
    start_round()

# Função para iniciar uma rodada
def start_round():
    if is_dealer():
        distribute_cards()
        start_betting()
    else:
        print("Aguardando início da rodada pelo dealer")


# Função para verificar se o nó atual é o dealer
def is_dealer():
    return current_node_index == dealer_index

# Função para distribuir cartas
def distribute_cards():
    suits = ['♦', '♠', '♥', '♣']
    ranks = ['4', '5', '6', '7', 'Q', 'J', 'K', 'A', '2', '3']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    cards_per_player = 14 - current_round  # Número de cartas por jogador diminui a cada rodada
    for i in range(len(nodes)):
        hand = random.sample(deck, cards_per_player)
        send_message(json.dumps({'type': 'CARDS', 'hand': hand}), i)

# Função para iniciar as apostas (uma aposta por jogador por rodada)
def start_betting():
    global bets
    bets = {}
    #is dealer adicionado
    if(token == True) and is_dealer():
        print(f"Iniciando apostas com jogador {current_node_index}")
        get_player_bet(current_node_index, (current_node_index + 1) % len(nodes))
    else:
        print("Aguardando início das apostas pelo dealer")

# Função para o jogador digitar sua aposta (uma aposta por jogador por rodada), para fazer a aposta o jogador deve ter o token
def get_player_bet(player_index, next_node_index):
    global token
    if token:
        while True:
            try:
                bet = int(input("Digite sua aposta: "))
                if bet >= 0 and bet <= 14 - current_round:
                    # Passa o bastão para o próximo jogador
                    pass_token(next_node_index)
                    # Envia a mensagem da aposta para todos os jogadores
                    for i in range(len(nodes)):
                        send_message(json.dumps({'type': 'BET', 'player': player_index, 'bet': bet, 'next_node': next_node_index}), i)
                    break
                else:
                    print("Aposta inválida. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número.")
    else:
        print(f"Aguardando aposta do jogador {next_node_index}")


# Função para verificar se o nó atual tem o token
def has_token():
    return token

# Função para lidar com cartas recebidas
def handle_cards(hand):
    global player_hand
    player_hand = hand
    print(f"Cartas recebidas: {player_hand}")

# Função para lidar com apostas 
def handle_bet(player, bet):
    global bets
    bets[player] = bet
    print(f"Aposta do jogador {player}: {bet}")
    if len(bets) >= len(nodes):
        print("Aguardando início do jogo")
        start_game()
    else:
        get_player_bet(current_node_index, (current_node_index + 1) % len(nodes))

# Função para iniciar o jogo após as apostas, Dealer inicia o jogo
def start_game():
    if is_dealer():
        print("Iniciando jogo como dealer")
        get_player_card(current_node_index, (current_node_index + 1) % len(nodes))
    else:
        print("Aguardando início do jogo pelo dealer")

# Função para lidar com jogadas, para fazer a jogada o jogador deve ter o token
def handle_play(player, card):
    global cards_played
    cards_played[player] = card
    print(f"Jogada do jogador {player}: {card}")
    if len(cards_played) >= len(nodes):
        print("Aguardando resultado da rodada")
        cards_analyzed = cards_played
        # Zerar valor de cards_played para as próximas jogadas
        cards_played = {}
        calculate_results(cards_analyzed)
    else:
        get_player_card(current_node_index, (current_node_index + 1) % len(nodes))

# Função para o jogador digitar sua aposta (uma aposta por jogador por rodada), para fazer a aposta o jogador deve ter o token
def get_player_card(player_index, next_node_index):
    global token
    if token:
        while True:
            print(f"Sua mão: {player_hand}")
            for idx, card in enumerate(player_hand):
                print(f"{idx}: {card}")
            try:
                index = int(input("Escolha o índice da carta para jogar: "))
                if 0 <= index < len(player_hand):
                    card = player_hand.pop(index)
                    print(f"Você jogou: {card}")
                    # Passa o bastão para o próximo jogador
                    pass_token(next_node_index)
                    # Envia a mensagem da carta jogada para todos os jogadores
                    for i in range(len(nodes)):
                        send_message(json.dumps({'type': 'PLAY', 'player': player_index, 'card': card}), i)
                    break
                else:
                    print("Índice inválido. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite uma carta válida.")
    else:
        print(f"Aguardando jogada do jogador {next_node_index}")

# Função para calcular resultados
def calculate_results(cards_analyzed):
    global player_wins, token
    winning_card = compare_cards(cards_analyzed)
    winning_player = [player for player, card in cards_analyzed.items() if card == winning_card][0]
    print("-----------------------------------")
    print(f"Jogador {winning_player} venceu com a carta {winning_card}")
    print("-----------------------------------")
    player_wins[winning_player] += 1
    if len(player_hand) == 0 and token == True:
        print("Aguardando resultado final")
        accounting_results(player_wins)
    elif len(player_hand) == 0:
        print("Aguardando resultado final")
    else:
        get_player_card(current_node_index, (current_node_index + 1) % len(nodes))

#Faça uma função que compara as cartas jogadas e retorna a carta vencedora
#Primeiro compara os ranks e depois os suits
#Exemplo: 3♣ > 3♥ > 3♠ > 3♦ > 2♣ > ... > 4♦
def compare_cards(cards_analyzed):
    suits = ['♣', '♥', '♠', '♦']
    ranks = ['3', '2', 'A', 'K', 'Q', 'J', '7', '6', '5', '4']
    winning_card = None
    for rank in ranks:
        for suit in suits:
            card = f"{rank}{suit}"
            if card in cards_analyzed.values():
                winning_card = card
                break
        if winning_card:
            break
    return winning_card

# Função para lidar com os resultados finais e a aposta de cada jogador
def accounting_results(player_wins):
    global player_scores, bets, results, token, nodes
    for i in range(len(nodes)):
        results[i] = abs(bets[i] - player_wins[i])
        if results[i] == 0:
            print(f"Jogador {i} cumpriu sua aposta") # == 0: player fez sua aposta, != 0: player não fez sua aposta
        else:
            print(f"Jogador {i} não cumpriu sua aposta")
    if token == True and dealer_index == current_node_index:
        for i in range(len(nodes)):
            send_message(json.dumps({'type': 'RESULT', 'results': results}), i)

# Função para lidar com resultados
def handle_result(results):
    global player_scores, bets, token, nodes
    scores = [0, 0, 0, 0]
    for i in range(len(nodes)):
        scores [i] = player_scores[i] - results[i]
        print(f"Score do jogador {i} = Score Atual: {player_scores[i]} - Penalidade: {results[i]} = {scores[i]}")
    

# Função para lidar com pontuações
def handle_score(scores):
    global player_scores
    player_scores = scores
    print(f"Pontuações atualizadas: {player_scores}")
    check_for_elimination()

# Função para verificar se algum jogador foi eliminado
def check_for_elimination():
    global player_scores, nodes, current_round
    for player, score in list(player_scores.items()):
        if score <= 0:
            print(f"Jogador {player} foi eliminado!")
            del player_scores[player]
            nodes.remove(nodes[player])
            if player == dealer_index:
                pass_token_to_next_dealer()


# Função para atualizar pontuações e passar o bastão
def update_scores_and_pass_token():
    global current_round
    for i in range(len(nodes)):
        send_message(json.dumps({'type': 'SCORE', 'scores': player_scores}), i)
    
    pass_token_to_next_dealer()
    #else:
    #    current_round += 1  # Incrementa a rodada após todas as cartas serem jogadas
    #    pass_token((dealer_index + 1) % len(nodes))

# Função para passar o bastão para o próximo nó para ser o novo dealer
def pass_token_to_next_dealer():
    global current_round, dealer_index
    current_round = current_round + 1
    dealer_index = (dealer_index + 1) % len(nodes)
    print(f"Passando o bastão para o próximo dealer: nó {dealer_index}")
    send_message("TOKEN", dealer_index)

# Handler para sinal de interrupção
def signal_handler(sig, frame):
    print('Encerrando o programa...')
    sock.close()
    sys.exit(0)

# Configura o handler para o sinal de interrupção
signal.signal(signal.SIGINT, signal_handler)

# Iniciar o processo de jogo
if __name__ == "__main__":
    print(f"Jogo iniciado no nó {current_node_index}")
    if current_node_index == 0:
        send_message("TOKEN", current_node_index)
        send_message(json.dumps({'type': 'START', 'dealer': dealer_index}), current_node_index)
    else:
        pass_token(dealer_index)
    while True:
        time.sleep(1)