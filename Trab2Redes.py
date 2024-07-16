import socket
import random
import json
import threading

#Ajustes
# Comunicação: máquinas estão na mesma rede e que as portas especificadas estão abertas
# Teste: Teste o código em um ambiente controlado para garantir que a comunicação entre as máquinas

# Endereços IP e portas das máquinas
machines = [
    ('192.168.0.1', 5001, 5002),
    ('192.168.0.2', 5003, 5004),
    ('192.168.0.3', 5005, 5006),
    ('192.168.0.4', 5007, 5008)
]

# Inicialização dos sockets
sockets = []
for ip, port_in, port_out in machines:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((ip, port_in))
    sockets.append(s)

# Função para enviar dados para a próxima máquina no anel
def send_to_next_machine(current_machine_index, data):
    next_machine_index = (current_machine_index + 1) % len(machines)
    next_machine = machines[next_machine_index]
    next_machine_ip = next_machine[0]
    next_machine_port = next_machine[2]  # Porta de entrada da próxima máquina
    sockets[current_machine_index].sendto(data.encode('utf-8'), (next_machine_ip, next_machine_port))

# Função para receber dados
def receive_data(machine_index):
    data, addr = sockets[machine_index].recvfrom(1024)
    return data.decode('utf-8')

# Inicialização do jogo
def initialize_game():
    # Distribuição de cartas
    cards = list(range(1, 13)) * 4  # Cartas de 1 a 12, quatro naipes
    random.shuffle(cards)
    hands = [cards[i::4] for i in range(4)]  # Distribui as cartas entre os 4 jogadores
    return hands

# Função principal do jogo
def main_game(machine_index):
    hands = initialize_game()
    scores = [0, 0, 0, 0]
    num_rounds = len(hands[0])  # Número de rodadas é o número de cartas por jogador

    for round_num in range(num_rounds):
        print(f"Round {round_num + 1}")
        declared_wins = [0, 0, 0, 0]

        for i in range(4):
            # Recebe a declaração de vitórias do jogador
            if i == machine_index:
                declaration = int(input("Quantas rodadas você vai ganhar? "))
                declared_wins[i] = declaration
                send_to_next_machine(i, json.dumps({"declaration": declaration}))
            else:
                data = receive_data(machine_index)
                declaration = json.loads(data)["declaration"]
                declared_wins[i] = declaration

        # Verifica se a soma das declarações é maior que o número de rodadas
        if sum(declared_wins) < num_rounds:
            declared_wins[0] += (num_rounds - sum(declared_wins))  # Carteador ajusta sua declaração

        # Jogadores jogam suas cartas
        played_cards = []
        for j in range(4):
            if j == machine_index:
                card = hands[j][round_num]
                print(f"Você joga a carta {card}")
                send_to_next_machine(j, json.dumps({"player": j, "card": card}))
            else:
                data = receive_data(machine_index)
                played_card = json.loads(data)
                played_cards.append((played_card["player"], played_card["card"]))

        # Determina o vencedor da rodada
        winner = max(played_cards, key=lambda x: x[1])[0]
        print(f"Jogador {winner + 1} ganha a rodada")
        scores[winner] += 1

    print("Pontuações finais:", scores)

if __name__ == "__main__":
    machine_index = int(input("Digite o índice da máquina (0-3): "))
    threading.Thread(target=main_game, args=(machine_index,)).start()
