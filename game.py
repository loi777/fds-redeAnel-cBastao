# Projeto: Jogo de Cartas usando Rede em anel
# Trabalho 2 da disciplina de Redes de Computadores 1 - 2024/1
# Professores: Luiz Carlos Pessoa Albini e Eduardo Todt
# Autores: Victor Ribeiro Garcia (GRR20203954) e Luiz Fernando Giongo dos Santos (GRR20203965)

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
total_nodes = len(nodes)
current_node_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
next_node_index = (current_node_index + 1) % total_nodes

# Variáveis globais
current_round = 1 # Round Inicial (iniciar com 1)
player_hand = []
bets = [0, 0, 0, 0] 
player_scores = [12, 12, 12, 12] # Scores Iniciais (iniciar com 12)
cards_played = [0, 0, 0, 0]     
results = [0, 0, 0, 0]     
player_wins = [0, 0, 0, 0]     
dealer_index = 0  # Dealer inicial (iniciar com 0)
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
    if token == True: # Só passa o token se o nó atual possuir o token
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
        handle_bet(message.get('player'), message.get('bet0'), message.get('bet1'), message.get('bet2'), message.get('bet3'))
    elif message_type == 'ALL_BETS':
        handle_all_bets(message.get('bet0'), message.get('bet1'), message.get('bet2'), message.get('bet3'))
    elif message_type == 'PLAY':
        handle_play(message.get('player'), message.get('card0'), message.get('card1'), message.get('card2'), message.get('card3'))
    elif message_type == 'ALL_PLAYS':
        handle_all_plays(message.get('card0'), message.get('card1'), message.get('card2'), message.get('card3'))
    else:
        print("Mensagem inválida")

# Função para lidar com o início do jogo
def handle_start(dealer):
    global dealer_index
    dealer_index = dealer
    print(f"Iniciando jogo com dealer {dealer}")
    start_round()

# Função para iniciar uma rodada
def start_round():
    global player_hand
    print(f"Iniciando rodada {current_round}")
    distribute_cards()

# Função para verificar se o nó atual é o dealer
def is_dealer():
    return current_node_index == dealer_index

# Função para distribuir cartas
def distribute_cards():
    suits = ['♦', '♠', '♥', '♣']
    ranks = ['4', '5', '6', '7', 'Q', 'J', 'K', 'A', '2', '3']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    if(current_round < 14):
        cards_per_player = 14 - current_round  # Número de cartas por jogador diminui a cada rodada
    else:
        cards_per_player = 1
    if (token == True):
        hand = random.sample(deck, cards_per_player)
        pass_token(next_node_index)
        send_message(json.dumps({'type': 'CARDS', 'hand': hand}), next_node_index)

# Função para lidar com as cartas recebidas 
def handle_cards(hand):
    global player_hand
    player_hand = hand
    print(f"Cartas recebidas: {player_hand}")
    if current_node_index == dealer_index:
        print("Aguardando início das apostas")
        start_betting()
    else:
        distribute_cards()

# Função para iniciar as apostas (uma aposta por jogador por rodada)
def start_betting():
    global bets
    bets = [-1, -1, -1, -1]
    #is dealer adicionado
    if(token == True) and is_dealer():
        print(f"Iniciando apostas com jogador {current_node_index}")
        get_player_bet(current_node_index, (current_node_index + 1) % len(nodes))
    else:
        print("Aguardando início das apostas pelo dealer")

# Função para o jogador digitar sua aposta (uma aposta por jogador por rodada), para fazer a aposta o jogador deve ter o token
def get_player_bet(player_index, next_node_index):
    global token, bets
    if token:
        while True:
            try:
                print(f"------------------------Rodada {current_round}---------------------------")
                print(f"Dealer Atual: {dealer_index}")
                print(f"Suas cartas: {player_hand}")
                if current_round < 14:
                    bet = int(input(f"Digite sua aposta (0-{14 - current_round}): "))
                    if bet >= 0 and bet <= 14 - current_round:
                        print("-------------------------------------------------------------")
                        pass_token(next_node_index)
                        bets[player_index] = bet
                        send_message(json.dumps({'type': 'BET', 'player': player_index, 'bet0': bets[0], 'bet1': bets[1], 'bet2': bets[2], 'bet3': bets[3], 'next_node': next_node_index}), next_node_index)
                        break
                    else:
                        print("Aposta inválida. Tente novamente.")
                else:
                    bet = int(input(f"Digite sua aposta (0-1): "))
                    if bet >= 0 and bet <= 1:
                        print("-------------------------------------------------------------")
                        pass_token(next_node_index)
                        bets[player_index] = bet
                        send_message(json.dumps({'type': 'BET', 'player': player_index, 'bet0': bets[0], 'bet1': bets[1], 'bet2': bets[2], 'bet3': bets[3], 'next_node': next_node_index}), next_node_index)
                        break
                    else:
                        print("Aposta inválida. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número.")
    else:
        print(f"Aguardando aposta do jogador {next_node_index}")

# Função para lidar com apostas 
def handle_bet(player, bet0, bet1, bet2, bet3):
    global bets
    bets[0] = bet0
    bets[1] = bet1
    bets[2] = bet2
    bets[3] = bet3
    if (len(bets) >= len(nodes)) and (token == True) and is_dealer():
        send_all_bets()
    else:
        get_player_bet(current_node_index, (current_node_index + 1) % len(nodes))

# Função para enviar as bets atualizadas
def send_all_bets():
    global bets
    pass_token(next_node_index)
    send_message(json.dumps({'type': 'ALL_BETS', 'bet0': bets[0], 'bet1': bets[1], 'bet2': bets[2], 'bet3': bets[3]}), (current_node_index + 1) % len(nodes))
    if dealer_index != current_node_index:
        print(f"Apostas recebidas: {bets}")

def handle_all_bets(bet0, bet1, bet2, bet3):
    global bets
    bets[0] = bet0
    bets[1] = bet1
    bets[2] = bet2
    bets[3] = bet3
    if (token == True) and is_dealer():
        print(f"Apostas recebidas: {bets}")
        start_game()
    else:
        send_all_bets()

# Função para iniciar o jogo após as apostas, Dealer inicia o jogo
def start_game():
    global cards_played
    cards_played = [-1, -1, -1, -1]
    print(f"Iniciando jogo com jogador {current_node_index}")
    if(token == True) and is_dealer():
        get_player_card(current_node_index, (current_node_index + 1) % len(nodes))

# Função para lidar com jogadas, para fazer a jogada o jogador deve ter o token
def handle_play(player, card0, card1, card2, card3):
    global cards_played
    cards_played[0] = card0
    cards_played[1] = card1
    cards_played[2] = card2
    cards_played[3] = card3
    print(f"Cartas jogadas: {cards_played}")
    if (len(cards_played) >= len(nodes)) and (token == True) and is_dealer():
        send_all_plays()
    else:
        get_player_card(current_node_index, (current_node_index + 1) % len(nodes))

# Função para enviar as jogadas atualizadas
def send_all_plays():
    global cards_played
    pass_token(next_node_index)
    send_message(json.dumps({'type': 'ALL_PLAYS', 'card0': cards_played[0], 'card1': cards_played[1], 'card2': cards_played[2], 'card3': cards_played[3], 'next_node': next_node_index}), (current_node_index + 1) % len(nodes))
    if dealer_index != current_node_index:
        print(f"Cartas jogadas: {cards_played}")
        calculate_results(cards_played)

def handle_all_plays(card0, card1, card2, card3):
    global cards_played
    cards_played[0] = card0
    cards_played[1] = card1
    cards_played[2] = card2
    cards_played[3] = card3
    if (token == True) and is_dealer():
        print(f"Cartas jogadas: {cards_played}")
        calculate_results(cards_played)
    else:
        send_all_plays()

# Função para o jogador digitar sua aposta (uma aposta por jogador por rodada), para fazer a aposta o jogador deve ter o token
def get_player_card(player_index, next_node_index):
    global token, cards_played
    if token:
        while True:
            print(f"------------Rodada {current_round}------------")
            print(f"Dealer Atual: {dealer_index}")
            print(f"Sua aposta: {bets[player_index]}")
            print(f"Jogadas vencidas: {player_wins[player_index]}")
            print(f"Cartas jogadas: {cards_played}")
            print(f"Sua mão: {player_hand}")
            for idx, card in enumerate(player_hand):
                print(f"{idx}: {card}")
            try:
                index = int(input("Escolha o índice da carta para jogar: "))
                if 0 <= index < len(player_hand):
                    print("------------------------------------------------")
                    card = player_hand.pop(index)
                    print(f"Você jogou: {card}")
                    # Passa o bastão para o próximo jogador
                    pass_token(next_node_index)
                    # Envia a mensagem da carta jogada para o proximo jogador
                    cards_played[player_index] = card
                    send_message(json.dumps({'type': 'PLAY', 'player': player_index, 'card0': cards_played[0], 'card1': cards_played[1], 'card2': cards_played[2], 'card3': cards_played[3], 'next_node': next_node_index}), next_node_index)
                    break
                else:
                    print("Índice inválido. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite uma carta válida.")
    else:
        print(f"Aguardando jogada do jogador {(current_node_index - 1) % total_nodes}")

# Função para calcular resultados
def calculate_results(cards_analyzed):
    global player_wins, token, cards_played
    winning_card = compare_cards(cards_analyzed)
    winning_player = None
    # Jogador que jogou a carta maior por ultimo vence
    for i in range(4):
        if cards_analyzed[i] == winning_card:
            winning_player = i
    print("-----------------------------------")
    print(f"Jogador {winning_player} venceu com a carta {winning_card}")
    print("-----------------------------------")
    cards_played = [-1, -1, -1, -1]
    player_wins[winning_player] += 1
    if len(player_hand) == 0:
        print("Calculando resultado final")
        accounting_results(player_wins)
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
            if card in cards_analyzed:
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
    give_result(results)

# Função para lidar com resultados
def give_result(results):
    global player_scores, bets, token, nodes
    scores = [0, 0, 0, 0]
    print(f"---------------------------------Rodada {current_round}-------------------------------------")
    for i in range(len(nodes)):
        scores [i] = player_scores[i] - results[i]
        if scores[i] <= 0:
            scores[i] = 0
        print(f"Score do jogador {i} = Score Atual: {player_scores[i]} - Penalidade: {results[i]} = {scores[i]}")
    give_score(scores)
    
# Função para lidar com pontuações
def give_score(scores):
    global player_scores
    player_scores = scores
    print(f"SUA PONTUAÇÃO ATUAL: {player_scores[current_node_index]}")
    print("------------------------------------------------------------------------------")
    check_for_elimination()

# Função para verificar se algum jogador foi eliminado
def check_for_elimination():
    global player_scores
    player_elimited = False
    for i in range(len(nodes)):
        if player_scores[i] <= 0:
            if i == current_node_index:
                player_elimited = True
                print(f"Você foi eliminado!")
            else:
                player_elimited = True
                print(f"Jogador {i} foi eliminado")
    if player_elimited == True:
        print(f"Obrigado por jogar, jogador {current_node_index}!")
        sock.close()
        sys.exit(0)
    else:
        time.sleep(5) 
    update_round_and_pass_token()

# Função para zerar os dados do round, incrimentar o round e passar o dealer
def update_round_and_pass_token():
    global current_round, dealer_index, token, player_hand, bets, cards_played, results, player_wins
    player_hand = []
    bets = [0, 0, 0, 0] 
    cards_played = [0, 0, 0, 0]     
    results = [0, 0, 0, 0]     
    player_wins = [0, 0, 0, 0]       
    current_round += 1
    if(token == True) and is_dealer():
        dealer_index = (dealer_index + 1) % len(nodes)
        print(f"Novo dealer: nó {dealer_index}")
        pass_token_to_next_dealer()
    else:
        dealer_index = (dealer_index + 1) % len(nodes)
        print(f"Novo dealer: nó {dealer_index}")
        token = False

# Função para passar o bastão para o próximo nó para ser o novo dealer e iniciar proxima rodada
def pass_token_to_next_dealer():
    global dealer_index
    pass_token(dealer_index)
    send_message(json.dumps({'type': 'START', 'dealer': dealer_index}), dealer_index)

# Handler para sinal de interrupção
def signal_handler(sig, frame):
    print('\nEncerrando o programa...')
    sock.close()
    sys.exit(0)

# Configura o handler para o sinal de interrupção
signal.signal(signal.SIGINT, signal_handler)

# Iniciar o processo de jogo
if __name__ == "__main__":
    print(f"Jogo iniciado no nó {current_node_index}")
    if current_node_index == 0:
        token = True
        print(f"Token: {token}")
        send_message(json.dumps({'type': 'START', 'dealer': dealer_index}), current_node_index)
    else:
        token = False
        print(f"Token: {token}")
    while True:
        time.sleep(1)