# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import snap7
from snap7.util import *
from pymodbus.client import ModbusTcpClient

'''
Komunikacja poprzez Snap7:
-> wysyłanie tablicy bool'i do DB 
-> odczytywanie tablicy bool' z DB
'''


def snap7_send_booleans(IP, DB_number, DB_start_byte, bool_values_to_send):
    data_sent_status = False
    plc_client = snap7.client.Client()
    try:
        plc_client.connect(IP, rack=0, slot=1)  # Default hardware configuration for PLC S7-1200

        if plc_client.get_connected():
            print(f"Connected to PLC at {IP}")
            bytes_required = (len(bool_values_to_send) + 7) // 8  # One byte = 8 bits
            buffer = plc_client.db_read(DB_number, DB_start_byte, bytes_required)

            for index, flag in enumerate(bool_values_to_send):
                byte_offset = index // 8  # Byte index
                bit_offset = index % 8    # Bit index within the byte
                set_bool(buffer, byte_offset, bit_offset, flag)
            plc_client.db_write(DB_number, DB_start_byte, buffer)
            data_sent_status = True
            print(f"Boolean sent to PLC in DB {DB_number} starting from byte {DB_start_byte}")

        else:
            print("Connection to PLC S7-1200 failed")
            data_sent_status = False
    finally:
        plc_client.disconnect()

    return data_sent_status

def snap7_read_booleans(IP, DB_number, DB_start_byte, num_of_bools):
    plc_client = snap7.client.Client()
    bool_values = []
    data_read_status = False
    try:
        plc_client.connect(IP, rack=0, slot=1)

        if plc_client.get_connected():
            print(f"Connected to PLC at {IP}")

            bytes_required = (num_of_bools + 7) // 8  # Każdy bajt to 8 bitów

            buffer = plc_client.db_read(DB_number, DB_start_byte, bytes_required) # Odczyt danych z Data Block

            # Wyciągnięcie wartości logicznych z bufora
            for index in range(num_of_bools):
                byte_offset = index // 8  # Indeks bajtu
                bit_offset = index % 8  # Indeks bitu w bajcie
                tmp = get_bool(buffer, byte_offset, bit_offset)
                bool_values.append(tmp)

            data_read_status = True
            print(f"Read {bool_values} from DB {DB_number}, byte {DB_start_byte}")
        else:
            print("Connection to PLC S7-1200 failed")

    finally:
        plc_client.disconnect()

    return data_read_status, bool_values


def snap7_send_strings(IP, DB_number, string_offsets, string_vector):
    STRING_LENGTH = 12
    TOTAL_STRING_SIZE = 14  # 2 bajty nagłówka + 12 znaków danych
    plc_client = snap7.client.Client()
    string_send_status = False

    try:
        # Połączenie z PLC
        plc_client.connect(IP, rack=0, slot=1)

        for offset, string_value in zip(string_offsets, string_vector):
            # Tworzenie bufora dla STRING
            buffer = bytearray(TOTAL_STRING_SIZE)  # Cały bufor musi mieć rozmiar 14 bajtów
            buffer[0] = STRING_LENGTH  # Maksymalna długość STRING
            buffer[1] = min(len(string_value), STRING_LENGTH)  # Aktualna długość STRING (max 12 znaków)

            # Wypełnij dane STRING (przytnij, jeśli jest za długi)
            for i in range(len(string_value[:STRING_LENGTH])):
                buffer[2 + i] = ord(string_value[i])  # ASCII znaków do bufora

            # Wypełnij pozostałe znaki zerami (dla wyrównania)
            for i in range(len(string_value), STRING_LENGTH):
                buffer[2 + i] = 0  # Puste bajty
            # Zapis danych do DB
            plc_client.db_write(DB_number, offset, buffer)

        string_send_status = True
        print("Stringi zostały pomyślnie wysłane do PLC.")

    except Exception as e:
        string_send_status = False
        print(f"Błąd podczas wysyłania danych do PLC: {e}")
    finally:
        # Rozłączenie z PLC
        plc_client.disconnect()

    return string_send_status

'''
Komunukacja poprzez Modbus TCP:
-> wysyłanie tablicy int do Holding Registers
-> oczytywanie z Holding Registers
'''

def modbus_TCP_send_holding_registers(plc_ip, default_port, HR_start_idx, values):

    data_sent_status = False
    client = ModbusTcpClient(host=plc_ip, port=default_port)

    try:
        if client.connect():
            print(f"PLC connected via MODBUS")
            send_result = client.write_registers(HR_start_idx, values)
            if send_result.isError():
                print("ERROR sending DATA")
                data_sent = False
            else:
                print("DATA has been sent successfully")
                data_sent = True
        else:
            print("Connection via MODBUS failed")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    finally:
        client.close()

    return data_sent_status

def modbus_TCP_read_holding_registers(plc_ip, default_port, HR_start_idx, count):

    data_read_status = False
    client = ModbusTcpClient(host=plc_ip, port=default_port)
    registers = None

    try:
        if client.connect():
            print("PLC connected via MODBUS")
            read_result = client.read_holding_registers(HR_start_idx, count)
            if read_result.isError():
                data_read = False
                print("ERROR reading holding registers")
            else:
                registers = read_result.registers
                data_read = True
                print(f"Holding registers from {HR_start_idx}: {registers}")
        else:
            print("Connection via MODBUS failed")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        client.close()

    return data_read_status, registers


def send_strings_to_modbus(plc_ip, modbus_port, start_address, string_vector):
    """
    Wysyła listę stringów do sterownika PLC za pomocą MODBUS TCP.

    Args:
        plc_ip (str): Adres IP sterownika PLC.
        modbus_port (int): Port Modbus TCP (zwykle 502).
        start_address (int): Adres początkowy w rejestrach Modbus.
        string_vector (list of str): Lista stringów do wysłania.

    Returns:
        None
    """
    try:
        # Połączenie z PLC przez Modbus TCP
        client = ModbusTcpClient(plc_ip, port=modbus_port)
        if not client.connect():
            raise ConnectionError("Nie udało się połączyć z PLC przez Modbus TCP.")

        for index, string_value in enumerate(string_vector):
            # Adres startowy dla bieżącego stringa
            address = start_address + index * 5  # Załóżmy maksymalnie 10 rejestrów na string

            # Zakodowanie stringa na rejestry Modbus
            registers = string_to_modbus_registers(string_value, max_length=20)

            # Wysłanie rejestrów do PLC
            result = client.write_registers(address, registers)
            if result.isError():
                raise Exception(f"Błąd przy zapisie stringa '{string_value}' na adres {address}.")

        print("Stringi zostały pomyślnie wysłane do PLC.")

    except Exception as e:
        print(f"Błąd podczas wysyłania stringów do PLC: {e}")
    finally:
        client.close()


def string_to_modbus_registers(input_string, max_length):
    """
    Koduje string do formatu Modbus (każdy rejestr to 2 znaki ASCII).

    Args:
        input_string (str): String do zakodowania.
        max_length (int): Maksymalna długość stringa w znakach.

    Returns:
        list of int: Lista rejestrów Modbus z zakodowanymi danymi.
    """
    # Przycięcie stringa do maksymalnej długości
    input_string = input_string[:max_length]

    # Zakodowanie znaków ASCII do rejestrów (2 znaki = 1 rejestr)
    registers = []
    for i in range(0, len(input_string), 2):
        high_byte = ord(input_string[i])  # Pierwszy znak
        low_byte = ord(input_string[i + 1]) if i + 1 < len(input_string) else 0  # Drugi znak (lub 0 jeśli brak)
        registers.append((high_byte << 8) + low_byte)

    return registers



# '''
# TESTOWANIE FUNKCJINALNOŚCI KOMUNIKACJI
# '''
#
# if __name__ == '__main__':
#
#     # Coonnection configuration
#     plc_ip_address = '192.168.10.10'
#
#     # MODBUS TCP CONFIGURATION
#     port = 502  # Default port Modbus TCP/IP
#
#     # WAREHOUSE STATE
#     warehouse_cells = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
#     warehouse_cells1 = [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
#
#     # SNAP7 CONFIGURATION
#     db_index = 20  # Data block number
#     start_position = 2  # Starting byte in the data block
#
#     # snap7_send_booleans(IP=plc_ip_address, DB_number=db_index, DB_start_byte=start_position, bool_values_to_send=warehouse_cells)
#     # res = snap7_read_booleans(IP=plc_ip_address, DB_number=20, DB_start_byte=0 , num_of_bools=1)
#     #
#     # string_vector = ["Hello", "World", "Siemens", "PLC", "TIA",
#     #                  "Portal", "Snap7", "Python", "Programming",
#     #                  "asd", "Offsets", "as"]
#     # string_offsets = [4, 260, 516, 772, 1028, 1284, 1540, 1796, 2052, 2308, 2564, 2820]
#     #
#     # snap7_send_strings(IP=plc_ip_address, DB_number=db_index, string_offsets=string_offsets ,string_vector=string_vector)
#
#     res = modbus_TCP_send_holding_registers(plc_ip=plc_ip_address, default_port=port, HR_start_idx=0, values=[0,1,1,1])
#     read_res, read_reg = modbus_TCP_read_holding_registers(plc_ip=plc_ip_address, default_port=port, HR_start_idx=21 , count=1)
#
#     start_address = 30  # Adres początkowy rejestrów
#     string_vector = ["Box1", "Box2", "Box3", "Box4", "Box5"]
#
#     send_strings_to_modbus(plc_ip_address, port, start_address, string_vector)


