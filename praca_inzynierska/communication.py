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

'''
Komunukacja poprzez Modbus TCP:
-> wysyłanie tablicy int do Holding Registers
-> oczytywanie z Holding Registers
'''

def modbus_TCP_send_holding_registers(plc_ip, default_port, HR_start_idx, values):

    data_sent = False
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

    return data_sent

def modbus_TCP_read_holding_registers(plc_ip, default_port, HR_start_idx, count):

    data_read = False
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

    return data_read, registers


'''
TESTOWANIE FUNKCJINALNOŚCI KOMUNIKACJI
'''

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
#     # communication_MODBUS_TCP(values_to_send=warehouse_cells, plc_ip=plc_ip_address, default_port=port)
#     snap7_send_booleans(IP=plc_ip_address, DB_number=db_index, DB_start_byte=start_position, bool_values_to_send=warehouse_cells)
#     res = snap7_read_booleans(IP=plc_ip_address, DB_number=20, DB_start_byte=0 , num_of_bools=1)
#
#     #res = modbus_TCP_send_holding_registers(plc_ip=plc_ip_address, default_port=port, HR_start_idx=19, values=[1,1,1,1])
#     # print(res)
#
#     #read_res, read_reg = modbus_TCP_read_holding_registers(plc_ip=plc_ip_address, default_port=port, HR_start_idx=21 , count=1)


