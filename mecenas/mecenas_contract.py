from electroncash.bitcoin import regenerate_key, MySigningKey, Hash
from electroncash.address import Address, Script, OpCodes as Op
from electroncash.transaction import Transaction,TYPE_ADDRESS
import ecdsa
from .contract import Contract
from math import ceil

import time
LOCKTIME_THRESHOLD = 500000000
UTXO=0
CONTRACT=1
MODE=2
PLEDGE_TIME=int((0*3600*24))#0.083
PLEDGE = 1000
PROTEGE = 0
MECENAS = 1
ESCROW = 2
MONTH=6*24#5062


def joinbytes(iterable):
    """Joins an iterable of bytes and/or integers into a single byte string"""
    return b''.join((bytes((x,)) if isinstance(x,int) else x) for x in iterable)


class MecenasContract(Contract):
    """Contract of Mecenas"""

    def __init__(self, addresses, initial_tx=None,v=0, data=None):
        Contract.__init__(self, addresses,initial_tx,v)
        self.participants=2
        try:
            self.i_time = data[0]
            self.rpayment = data[1]
        except:
            print("except")
            self.rpayment = PLEDGE
            self.i_time = PLEDGE_TIME // 512

        self.i_time_bytes = self.i_time.to_bytes(2, 'little', signed=True)
        try:
            self.i_time_bytes_mec = (self.i_time+MONTH).to_bytes(2, 'little', signed=True) # time + 1 month for mecenas
        except:
            if self.version !=2:
                self.i_time_bytes_mec = self.i_time_bytes
                pass

        assert self.rpayment >= 0
        assert self.i_time >= 0

        try:
            self.rpayment_bytes = self.rpayment.to_bytes(ceil(self.rpayment.bit_length() / 8), 'little', signed=True)
        except OverflowError:
            self.rpayment_bytes = self.rpayment.to_bytes(ceil(self.rpayment.bit_length() / 8)+1, 'little', signed=True)

        assert len(self.i_time_bytes) == 2
        assert len(self.rpayment_bytes) < 76 # Better safe than sorry
        

        ## Legacy version of Mecenas script
        self.redeemscript_v1 = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(self.rpayment_bytes), self.rpayment_bytes,
            Op.OP_3, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
            Op.OP_IF,
                Op.OP_10, Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP, Op.OP_4, Op.OP_EQUALVERIFY, Op.OP_9, Op.OP_PICK, Op.OP_SIZE,
                Op.OP_NIP, 1, 100, Op.OP_EQUALVERIFY, Op.OP_7, Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP, Op.OP_8,
                Op.OP_EQUALVERIFY, Op.OP_6, Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP, Op.OP_4, Op.OP_EQUALVERIFY, Op.OP_5,
                Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP, 1, 32, Op.OP_EQUALVERIFY, Op.OP_4, Op.OP_PICK, Op.OP_SIZE, Op.OP_NIP,
                Op.OP_8, Op.OP_EQUALVERIFY, Op.OP_11, Op.OP_PICK, Op.OP_13, Op.OP_PICK, Op.OP_CHECKSIGVERIFY, Op.OP_10,
                Op.OP_PICK, Op.OP_10, Op.OP_PICK, Op.OP_CAT, Op.OP_9, Op.OP_PICK, Op.OP_CAT, Op.OP_8, Op.OP_PICK, Op.OP_CAT,
                Op.OP_7, Op.OP_PICK, Op.OP_CAT, Op.OP_6, Op.OP_PICK, Op.OP_CAT, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_12,
                Op.OP_PICK, Op.OP_SIZE, Op.OP_1SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_OVER, Op.OP_SHA256, Op.OP_15, Op.OP_PICK,
                Op.OP_CHECKDATASIGVERIFY, 2, 232, 3, Op.OP_2, Op.OP_PICK, Op.OP_8, Op.OP_NUM2BIN, Op.OP_10, Op.OP_PICK,
                Op.OP_BIN2NUM, Op.OP_4, Op.OP_PICK, Op.OP_SUB, Op.OP_2, Op.OP_PICK, Op.OP_SUB, Op.OP_8, Op.OP_NUM2BIN, 1,
                118, 1, 135, 1, 169, 1, 20, 1, 23, 1, 25, 1, 136, 1, 172, 1, 20, Op.OP_PICK, Op.OP_3, Op.OP_SPLIT,
                Op.OP_NIP, 3, self.i_time_bytes, 64, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP, 1, 23, Op.OP_PICK, Op.OP_BIN2NUM, Op.OP_2,
                Op.OP_GREATERTHANOREQUAL, Op.OP_VERIFY, Op.OP_9, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_7,
                Op.OP_PICK, Op.OP_CAT, Op.OP_6, Op.OP_PICK, Op.OP_CAT, Op.OP_OVER, Op.OP_HASH160, Op.OP_CAT, Op.OP_8,
                Op.OP_PICK, Op.OP_CAT, Op.OP_11, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_10, Op.OP_PICK,
                Op.OP_CAT, Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_7, Op.OP_PICK, Op.OP_CAT, 1, 17, Op.OP_PICK, Op.OP_CAT,
                Op.OP_4, Op.OP_PICK, Op.OP_CAT, Op.OP_3, Op.OP_PICK, Op.OP_CAT, Op.OP_2DUP, Op.OP_CAT, Op.OP_HASH256, 1, 21,
                Op.OP_PICK, Op.OP_EQUAL, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
                Op.OP_3, Op.OP_PICK, Op.OP_2, Op.OP_EQUAL,
                Op.OP_IF,
                    Op.OP_5, Op.OP_PICK, Op.OP_HASH160, Op.OP_2, Op.OP_PICK, Op.OP_EQUALVERIFY, Op.OP_4, Op.OP_PICK, Op.OP_6,
                    Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_ELSE,
                    Op.OP_FALSE,
                Op.OP_ENDIF,
            Op.OP_ENDIF

        ])

        # Current version of Mecenas script
        self.redeemscript_v1_1 = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(self.rpayment_bytes), self.rpayment_bytes,
            3, self.i_time_bytes, 64,
            Op.OP_4, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
            Op.OP_IF,
            Op.OP_5, Op.OP_PICK, Op.OP_4, Op.OP_SPLIT, Op.OP_DROP, Op.OP_6, Op.OP_PICK, Op.OP_DUP, Op.OP_SIZE,
            Op.OP_NIP, 1, 40, Op.OP_SUB, Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, 1, 32, Op.OP_SPLIT, Op.OP_DROP, Op.OP_8,
            Op.OP_PICK, Op.OP_DUP, Op.OP_SIZE, Op.OP_NIP, 1, 44, Op.OP_SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_DUP, 1, 104,
            Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, Op.OP_OVER, Op.OP_SIZE, Op.OP_NIP, Op.OP_8, Op.OP_SUB, Op.OP_SPLIT,
            Op.OP_13, Op.OP_PICK, Op.OP_15, Op.OP_PICK, Op.OP_CHECKSIGVERIFY, Op.OP_13, Op.OP_PICK, Op.OP_SIZE,
            Op.OP_1SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_13, Op.OP_PICK, Op.OP_SHA256, Op.OP_16, Op.OP_PICK,
            Op.OP_CHECKDATASIGVERIFY, 2, 232, 3, Op.OP_9, Op.OP_PICK, Op.OP_8, Op.OP_NUM2BIN, Op.OP_2, Op.OP_PICK,
            Op.OP_BIN2NUM, Op.OP_11, Op.OP_PICK, Op.OP_SUB, Op.OP_2, Op.OP_PICK, Op.OP_SUB, Op.OP_8, Op.OP_NUM2BIN, 1,
            118, 1, 135, 1, 169, 1, 20, 1, 23, 1, 25, 1, 136, 1, 172, Op.OP_12, Op.OP_PICK, Op.OP_3, Op.OP_SPLIT,
            Op.OP_NIP, 1, 19, Op.OP_PICK, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP, 1, 18, Op.OP_PICK, Op.OP_BIN2NUM,
            Op.OP_2, Op.OP_GREATERTHANOREQUAL, Op.OP_VERIFY, Op.OP_9, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT,
            Op.OP_7, Op.OP_PICK, Op.OP_CAT, Op.OP_6, Op.OP_PICK, Op.OP_CAT, Op.OP_OVER, Op.OP_HASH160, Op.OP_CAT,
            Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_11, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_10, Op.OP_PICK,
            Op.OP_CAT, Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_7, Op.OP_PICK, Op.OP_CAT, 1, 24, Op.OP_PICK, Op.OP_CAT,
            Op.OP_4, Op.OP_PICK, Op.OP_CAT, Op.OP_3, Op.OP_PICK, Op.OP_CAT, Op.OP_2DUP, Op.OP_CAT, Op.OP_HASH256, 1, 19,
            Op.OP_PICK, Op.OP_EQUAL, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
            Op.OP_4, Op.OP_PICK, Op.OP_2, Op.OP_EQUAL,
            Op.OP_IF,
            Op.OP_6, Op.OP_PICK, Op.OP_HASH160, Op.OP_3, Op.OP_PICK, Op.OP_EQUALVERIFY, Op.OP_5, Op.OP_PICK, Op.OP_7,
            Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
            Op.OP_FALSE, Op.OP_ENDIF, Op.OP_ENDIF

        ])
        ## version with locktime for mecenas
        self.redeemscript_v2 = joinbytes([
            len(addresses[0].hash160), addresses[0].hash160,
            len(addresses[1].hash160), addresses[1].hash160,
            len(self.rpayment_bytes), self.rpayment_bytes,
            3, self.i_time_bytes, 64,
            3, self.i_time_bytes_mec, 64,
            Op.OP_5, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
            Op.OP_IF,
            Op.OP_6, Op.OP_PICK, Op.OP_4, Op.OP_SPLIT, Op.OP_DROP, Op.OP_7, Op.OP_PICK, Op.OP_DUP, Op.OP_SIZE,
            Op.OP_NIP, 1, 40, Op.OP_SUB, Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, 1, 32, Op.OP_SPLIT, Op.OP_DROP, Op.OP_9,
            Op.OP_PICK, Op.OP_DUP, Op.OP_SIZE, Op.OP_NIP, 1, 44, Op.OP_SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_DUP, 1, 104,
            Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, Op.OP_OVER, Op.OP_SIZE, Op.OP_NIP, Op.OP_8, Op.OP_SUB, Op.OP_SPLIT,
            Op.OP_14, Op.OP_PICK, Op.OP_16, Op.OP_PICK, Op.OP_CHECKSIGVERIFY, Op.OP_14, Op.OP_PICK, Op.OP_SIZE,
            Op.OP_1SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_14, Op.OP_PICK, Op.OP_SHA256, 1, 17, Op.OP_PICK,
            Op.OP_CHECKDATASIGVERIFY, 2, 232, 3, Op.OP_10, Op.OP_PICK, Op.OP_8, Op.OP_NUM2BIN, Op.OP_2, Op.OP_PICK,
            Op.OP_BIN2NUM, Op.OP_12, Op.OP_PICK, Op.OP_SUB, Op.OP_2, Op.OP_PICK, Op.OP_SUB, Op.OP_8, Op.OP_NUM2BIN, 1,
            118, 1, 135, 1, 169, 1, 20, 1, 23, 1, 25, 1, 136, 1, 172, Op.OP_12, Op.OP_PICK, Op.OP_3, Op.OP_SPLIT,
            Op.OP_NIP, 1, 20, Op.OP_PICK, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP, 1, 18, Op.OP_PICK, Op.OP_BIN2NUM,
            Op.OP_2, Op.OP_GREATERTHANOREQUAL, Op.OP_VERIFY, Op.OP_9, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT,
            Op.OP_7, Op.OP_PICK, Op.OP_CAT, Op.OP_6, Op.OP_PICK, Op.OP_CAT, Op.OP_OVER, Op.OP_HASH160, Op.OP_CAT,
            Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_11, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_10, Op.OP_PICK,
            Op.OP_CAT, Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_7, Op.OP_PICK, Op.OP_CAT, 1, 25, Op.OP_PICK, Op.OP_CAT,
            Op.OP_4, Op.OP_PICK, Op.OP_CAT, Op.OP_3, Op.OP_PICK, Op.OP_CAT, Op.OP_2DUP, Op.OP_CAT, Op.OP_HASH256, 1, 19,
            Op.OP_PICK, Op.OP_EQUAL, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
            Op.OP_5, Op.OP_PICK, Op.OP_2, Op.OP_EQUAL,
            Op.OP_IF,
            Op.OP_DUP, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP, Op.OP_7, Op.OP_PICK, Op.OP_HASH160, Op.OP_4, Op.OP_PICK,
            Op.OP_EQUALVERIFY, Op.OP_6, Op.OP_PICK, Op.OP_8, Op.OP_PICK, Op.OP_CHECKSIG, Op.OP_NIP, Op.OP_NIP,
            Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
            Op.OP_ELSE,
            Op.OP_FALSE, Op.OP_ENDIF, Op.OP_ENDIF

        ])
        ## Escrow version of Mecenas
        if len(addresses)==3:
            self.redeemscript_v3 = joinbytes([
                len(addresses[0].hash160), addresses[0].hash160,
                len(addresses[1].hash160), addresses[1].hash160,
                len(addresses[2].hash160), addresses[2].hash160,
                len(self.rpayment_bytes), self.rpayment_bytes,
                3, self.i_time_bytes, 64,
                Op.OP_5, Op.OP_PICK, Op.OP_TRUE, Op.OP_EQUAL,
                Op.OP_IF,
                Op.OP_6, Op.OP_PICK, Op.OP_4, Op.OP_SPLIT, Op.OP_DROP, Op.OP_7, Op.OP_PICK, Op.OP_DUP, Op.OP_SIZE,
                Op.OP_NIP, 1, 40, Op.OP_SUB, Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, 1, 32, Op.OP_SPLIT, Op.OP_DROP, Op.OP_9,
                Op.OP_PICK, Op.OP_DUP, Op.OP_SIZE, Op.OP_NIP, 1, 44, Op.OP_SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_DUP, 1,
                104, Op.OP_SPLIT, Op.OP_NIP, Op.OP_DUP, Op.OP_OVER, Op.OP_SIZE, Op.OP_NIP, Op.OP_8, Op.OP_SUB,
                Op.OP_SPLIT, Op.OP_14, Op.OP_PICK, Op.OP_16, Op.OP_PICK, Op.OP_CHECKSIGVERIFY, Op.OP_14, Op.OP_PICK,
                Op.OP_SIZE, Op.OP_1SUB, Op.OP_SPLIT, Op.OP_DROP, Op.OP_14, Op.OP_PICK, Op.OP_SHA256, 1, 17, Op.OP_PICK,
                Op.OP_CHECKDATASIGVERIFY, 2, 220, 5, Op.OP_9, Op.OP_PICK, Op.OP_8, Op.OP_NUM2BIN, Op.OP_2, Op.OP_PICK,
                Op.OP_BIN2NUM, Op.OP_11, Op.OP_PICK, Op.OP_SUB, Op.OP_2, Op.OP_PICK, Op.OP_SUB, Op.OP_8, Op.OP_NUM2BIN,
                1, 118, 1, 135, 1, 169, 1, 20, 1, 23, 1, 25, 1, 136, 1, 172, Op.OP_12, Op.OP_PICK, Op.OP_3, Op.OP_SPLIT,
                Op.OP_NIP, 1, 19, Op.OP_PICK, Op.OP_CHECKSEQUENCEVERIFY, Op.OP_DROP, 1, 18, Op.OP_PICK, Op.OP_BIN2NUM,
                Op.OP_2, Op.OP_GREATERTHANOREQUAL, Op.OP_VERIFY, Op.OP_9, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT,
                Op.OP_7, Op.OP_PICK, Op.OP_CAT, Op.OP_6, Op.OP_PICK, Op.OP_CAT, Op.OP_OVER, Op.OP_HASH160, Op.OP_CAT,
                Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_11, Op.OP_PICK, Op.OP_5, Op.OP_PICK, Op.OP_CAT, Op.OP_10,
                Op.OP_PICK, Op.OP_CAT, Op.OP_8, Op.OP_PICK, Op.OP_CAT, Op.OP_7, Op.OP_PICK, Op.OP_CAT, 1, 25,
                Op.OP_PICK, Op.OP_CAT, Op.OP_4, Op.OP_PICK, Op.OP_CAT, Op.OP_3, Op.OP_PICK, Op.OP_CAT, Op.OP_2DUP,
                Op.OP_CAT, Op.OP_HASH256, 1, 19, Op.OP_PICK, Op.OP_EQUAL, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_ELSE,
                Op.OP_5, Op.OP_PICK, Op.OP_2, Op.OP_EQUAL,
                Op.OP_IF,
                Op.OP_9, Op.OP_PICK, Op.OP_HASH160, Op.OP_5, Op.OP_PICK, Op.OP_EQUAL, Op.OP_10, Op.OP_PICK,
                Op.OP_HASH160, Op.OP_5, Op.OP_PICK, Op.OP_EQUAL, Op.OP_BOOLOR, Op.OP_VERIFY, Op.OP_8, Op.OP_PICK,
                Op.OP_HASH160, Op.OP_3, Op.OP_PICK, Op.OP_EQUAL, Op.OP_9, Op.OP_PICK, Op.OP_HASH160, Op.OP_5,
                Op.OP_PICK, Op.OP_EQUAL, Op.OP_BOOLOR, Op.OP_VERIFY, Op.OP_9, Op.OP_PICK, Op.OP_9, Op.OP_PICK,
                Op.OP_EQUAL, Op.OP_NOT, Op.OP_VERIFY, Op.OP_FALSE, Op.OP_7, Op.OP_PICK, Op.OP_7, Op.OP_PICK, Op.OP_2,
                Op.OP_11, Op.OP_PICK, Op.OP_11, Op.OP_PICK, Op.OP_2, Op.OP_CHECKMULTISIG, Op.OP_NIP, Op.OP_NIP,
                Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP, Op.OP_NIP,
                Op.OP_ELSE,
                Op.OP_FALSE, Op.OP_ENDIF, Op.OP_ENDIF

            ])


        self.redeemscript=self.redeemscript_v1
        self.set_version(v)
        self.address = Address.from_multisig_script(self.redeemscript)
        data1 = self.address.to_ui_string() + ' ' + str(self.version)
        data2 = str(self.i_time) + ' ' + str(self.rpayment)
        self.op_return = joinbytes(
            [Op.OP_RETURN, 4, b'>sh\x00', len(data1), data1.encode('utf8'), len(data2), data2.encode('utf8')])

        #assert 76 < len(self.redeemscript) <= 255  # simplify push in scriptsig; note len is around 200.
    @staticmethod
    def participants(version):
        if version == 3:
            return 3
        else:
            return 2



    def set_version(self, v):
        if v == 1:
            self.version = 1
            self.redeemscript = self.redeemscript_v1
        elif v == 1.1:
            self.version = 1.1
            self.redeemscript = self.redeemscript_v1_1
        elif v == 2:
            self.version = 2
            self.redeemscript = self.redeemscript_v2
        elif v == 3:
            self.version = 3
            self.participants = 3
            self.redeemscript = self.redeemscript_v3
        else:
            self.version = 1
            self.redeemscript = self.redeemscript_v1
            

class ContractManager:
    """A device that spends from a Mecenas Contract in two different ways."""
    def __init__(self, contract_tuple_list, keypairs, public_keys, wallet):
        self.contract_tuple_list = contract_tuple_list
        self.contract_index=0
        self.chosen_utxo = 0
        self.tx = contract_tuple_list[self.contract_index][UTXO][self.chosen_utxo]
        self.contract = contract_tuple_list[self.contract_index][CONTRACT]
        self.mode = contract_tuple_list[self.contract_index][MODE][0]
        self.keypair = keypairs
        self.pubkeys = public_keys
        self.wallet = wallet
        self.fee = 1000
        self.rpayment = self.contract.rpayment
        self.dummy_scriptsig = '00'*(110 + len(self.contract.redeemscript))
        self.version = self.contract.version
        self.script_pub_key = Script.P2SH_script(self.contract.address.hash160).hex()

        if self.mode == PROTEGE:
            self.sequence=2**22+self.contract.i_time
        else:
            self.sequence = 0
        self.value = int(self.tx.get('value'))
        self.txin = dict()

    def choice(self, contract_tuple, utxo_index, m):
        self.value=0
        self.txin=[]
        self.chosen_utxo=utxo_index
        self.contract = contract_tuple[CONTRACT]
        self.contract_index = self.contract_tuple_list.index(contract_tuple)
        self.rpayment = self.contract.rpayment
        self.mode = m
        self.version = contract_tuple[CONTRACT].version
        if self.version == 3:
            self.fee = 1500
        else:
            self.fee = 1000
        if self.mode == PROTEGE:
            self.sequence=2**22+self.contract.i_time
        elif self.mode == MECENAS and self.contract.version == 2:
            self.sequence=2**22+self.contract.i_time+MONTH
        else:
            self.sequence = 0
        sigs = 1
        if self.contract.version == 3:
            sigs =2
        utxo = contract_tuple[UTXO][utxo_index]
        if (utxo_index == -1) and (self.mode != PROTEGE):
            for u in contract_tuple[UTXO]:
                self.value += int(u.get('value'))
                self.txin.append( dict(
                    prevout_hash=u.get('tx_hash'),
                    prevout_n=int(u.get('tx_pos')),
                    sequence=self.sequence,
                    scriptSig=self.dummy_scriptsig,
                    type='unknown',
                    address=self.contract.address,
                    scriptCode=self.contract.redeemscript.hex(),
                    num_sig=1,
                    signatures=[None],
                    x_pubkeys=[self.pubkeys[self.contract_index][self.mode]],
                    value=int(u.get('value')),
                ))
        else:
            self.value = int(utxo.get('value'))
            self.txin = [dict(
                prevout_hash=utxo.get('tx_hash'),
                prevout_n=int(utxo.get('tx_pos')),
                sequence=self.sequence,
                scriptSig=self.dummy_scriptsig,
                type='unknown',
                address=self.contract.address,
                scriptCode=self.contract.redeemscript.hex(),
                num_sig=1,
                signatures=[None],
                x_pubkeys=[self.pubkeys[self.contract_index][self.mode]],
                value=int(utxo.get('value')),
            )]


    def complete_method(self, action='default'):
        print("completion_method",self.mode,self.version)
        if self.mode == PROTEGE and self.version == 1 :
            return self.completetx_ref
        if self.mode == PROTEGE and self.version == 3 and action == 'end':
            return self.completetx_multisig
        if self.mode == PROTEGE and (self.version == 1.1 or self.version ==2 or self.version == 3):
            print("completion method ok")
            return self.complete_covenant
        if self.mode == MECENAS and self.version != 3:
            return self.completetx
        if (self.mode == MECENAS and self.version == 3) or self.mode == ESCROW:
            return self.completetx_multisig


    def signtx(self, tx):
        """generic tx signer for compressed pubkey"""
        print("signing")
        tx.sign(self.keypair)

    def end_tx(self, inputs):
        outputs = [
            (TYPE_ADDRESS, self.contract.addresses[MECENAS], self.value)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        fee = 2*(len(tx.serialize(True)) // 2 + 1)
        if fee > self.value:
            raise Exception("Not enough funds to make the transaction!")
        outputs = [
            (TYPE_ADDRESS, self.contract.addresses[self.mode], self.value - fee)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        return tx

    def pledge_tx(self):
        inputs = self.txin
        outputs = [
            (TYPE_ADDRESS, self.contract.address, self.value - self.fee - self.rpayment),
            (TYPE_ADDRESS, self.contract.addresses[PROTEGE], self.rpayment)        ]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        #print(tx.outputs())
        return tx

    def completetx(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`).
        This works on multiple utxos if needed.
        """
        print("completing")
        pub = bytes.fromhex(self.pubkeys[self.contract_index][self.mode])
        for txin in tx.inputs():
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            if txin['scriptSig'] == self.dummy_scriptsig:
                script = [
                    len(pub), pub,
                    len(sig), sig,
                    Op.OP_2, 77, len(self.contract.redeemscript).to_bytes(2, 'little'), self.contract.redeemscript,
                    ]
                print("scriptSig length " + str(joinbytes(script).hex().__sizeof__()))
                txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()


    def completetx_multisig(self, tx):
        """
        Completes transaction by creating scriptSig. You need to sign the
        transaction before using this (see `signtx`).
        This works on multiple utxos if needed.
        """
        print("completing multisig")
        print(self.contract.address)
        for txin in tx.inputs():
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            print("addr ok")
            sig1 = txin['signatures'][0]
            sig2 = txin['signatures'][1]
            pub1 = txin['x_pubkeys'][0]
            pub2 = txin['x_pubkeys'][1]
            if not (sig1 and sig2 and pub1 and pub2):
                continue
            sig1 = bytes.fromhex(txin['signatures'][0])
            sig2 = bytes.fromhex(txin['signatures'][1])
            pub1 = bytes.fromhex(txin['x_pubkeys'][0])
            pub2 = bytes.fromhex(txin['x_pubkeys'][1])
            if txin['scriptSig'] == self.dummy_scriptsig:
                script = [
                    # len(pub2), pub2,
                    # len(pub1), pub1,
                    # len(sig2), sig2,
                    # len(sig1), sig1,
                    len(pub1), pub1,
                    len(pub2), pub2,
                    len(sig1), sig1,
                    len(sig2), sig2,
                    Op.OP_2, 77, len(self.contract.redeemscript).to_bytes(2, 'little'), self.contract.redeemscript,
                    ]
                print("scriptSig length " + str(joinbytes(script).hex().__sizeof__()))
                txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()

    def completetx_ref(self, tx):
        pub = bytes.fromhex(self.pubkeys[self.contract_index][self.mode])
        print("complete_ref")
        for i, txin in enumerate(tx.inputs()):
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            preimage=bytes.fromhex(tx.serialize_preimage(i))
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            print("Signature size:" + str(len(sig)))
            if txin['scriptSig'] == self.dummy_scriptsig:
                #self.checkd_data_sig(sig, preimage, self.pubkeys[self.contract_index][self.mode])

                ver=preimage[:4]
                hPhSo=preimage[4:104]
                scriptCode=preimage[104:-52]
                value=preimage[-52:-44]
                nSequence=preimage[-44:-40]
                hashOutput=preimage[-40:-8]
                tail=preimage[-8:]


                script = [
                    len(pub), pub,
                    len(sig), sig,
                    len(ver), ver,
                    76, len(hPhSo), hPhSo,
                    77, len(scriptCode).to_bytes(2, 'little'), scriptCode,
                    len(value), value,
                    len(nSequence), nSequence,
                    len(hashOutput), hashOutput,
                    len(tail), tail,
                    Op.OP_1, 77, len(self.contract.redeemscript).to_bytes(2, 'little'), self.contract.redeemscript,
                    ]
                print("scriptSig length "+ str(joinbytes(script).hex().__sizeof__()))
                txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()


    def complete_covenant(self, tx):
        pub = bytes.fromhex(self.pubkeys[self.contract_index][self.mode])
        print("complete_covenant")
        for i, txin in enumerate(tx.inputs()):
            # find matching inputs
            if txin['address'] != self.contract.address:
                continue
            preimage=bytes.fromhex(tx.serialize_preimage(i))
            sig = txin['signatures'][0]
            if not sig:
                continue
            sig = bytes.fromhex(sig)
            print("Signature size:" + str(len(sig)))
            if txin['scriptSig'] == self.dummy_scriptsig:
                #self.checkd_data_sig(sig,preimage,pub)
                script = [
                    len(pub), pub,
                    len(sig), sig,
                    77, len(preimage).to_bytes(2, byteorder='little'), preimage,
                    Op.OP_1, 77, len(self.contract.redeemscript).to_bytes(2,'little'), self.contract.redeemscript,
                    ]
                print("scriptSig length "+ str(joinbytes(script).hex().__sizeof__()))
            txin['scriptSig'] = joinbytes(script).hex()
        # need to update the raw, otherwise weird stuff happens.
        tx.raw = tx.serialize()


    def checkd_data_sig(self,sig,pre,pk):
        sec, compressed = self.keypair.get(pk)
        pre_hash = Hash(pre)
        pkey = regenerate_key(sec)
        secexp = pkey.secret
        private_key = MySigningKey.from_secret_exponent(secexp, curve=ecdsa.SECP256k1)
        public_key = private_key.get_verifying_key()
        print("Data signature ok:")
        print(public_key.verify_digest(sig[:-1], pre_hash, sigdecode=ecdsa.util.sigdecode_der))

