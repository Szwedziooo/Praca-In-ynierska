# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import snap7
from snap7.util import *
from pymodbus.client import ModbusTcpClient


def communication_Snap7(IP, DB_number, DB_start_byte, bool_values_to_send):
    print("Connection between Raspberry PI 4 and PLC SIEMENS s7-1200 via Snap7 Driver")
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
            print(f"Boolean sent to PLC in DB {DB_number} starting from byte {DB_start_byte}")
        else:
            print("Connection to PLC S7-1200 failed")
    finally:
        plc_client.disconnect()


def communication_MODBUS_TCP(values_to_send, plc_ip, default_port):

    # Modbus TCP Client
    client = ModbusTcpClient(plc_ip, port=default_port)
    print("Connection between Raspberry PI 4 -> PLC SIEMENS s7-1200 through MODBUS TCP/IP ")

    if client.connect():
        print("Connected with PLC s7-1200")

        # Reading holding registers from adress 0 - lenght 12
        result = client.read_holding_registers(0, 12)

        if result.isError():
            print("Reading ERROR:", result)
        else:
            print("Read values:", result.registers)

        # (holding register nr, value)
        write_result = client.write_registers(0, values_to_send)

        if write_result.isError():
            print("Sending data to reg ERROR:", write_result)
        else:
            print("Succesfully sent data to PLC")

        # Zakonczenie polaczenia
        client.close()

    else:
        print("Modbus connection failed")

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
#     warehouse_cells = [1, 1, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0]
#
#     # SNAP7 CONFIGURATION
#     db_index = 16  # Data block number
#     start_position = 0  # Starting byte in the data block
#
#     # communication_MODBUS_TCP(values_to_send=warehouse_cells, plc_ip=plc_ip_address, default_port=port)
#     communication_Snap7(IP=plc_ip_address, DB_number=db_index, DB_start_byte=start_position, bool_values_to_send=warehouse_cells)
#
#
# # See PyCharm help at https://www.jetbrains.com/help/pycharm/
