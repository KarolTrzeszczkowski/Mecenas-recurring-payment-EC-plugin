from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import electroncash.web as web
import webbrowser
from .mecenas_contract import MecenasContract
from electroncash.address import ScriptOutput, OpCodes, Address, Script
from electroncash.transaction import Transaction,TYPE_ADDRESS, TYPE_SCRIPT, SerializationError
from electroncash_gui.qt.amountedit  import BTCAmountEdit
from electroncash.i18n import _
from electroncash_gui.qt.util import *
from electroncash.wallet import Multisig_Wallet, ImportedPrivkeyWallet
from electroncash.util import NotEnoughFunds, ServerErrorResponse
from electroncash_gui.qt.transaction_dialog import show_transaction

from .contract_finder import find_contract_in_wallet
from .mecenas_contract import ContractManager, UTXO, CONTRACT, MODE, PROTEGE, MECENAS, ESCROW
from .util import *
from math import ceil
import json


class Intro(QDialog, MessageBoxMixin):

    def __init__(self, parent, plugin, wallet_name, password, manager=None):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        self.contract_tuple_list=None
        self.contractTx=None
        self.manager=None
        self.password = None
        self.mode=0
        hbox = QHBoxLayout()
        if is_expired():
            l = QLabel(_("Please update your plugin"))
            l.setStyleSheet("QLabel {color:#ff0000}")
            vbox.addWidget(l)
        l = QLabel("<b>%s</b>"%(_("Manage my Mecenas:")))
        vbox.addWidget(l)

        vbox.addLayout(hbox)
        b = QPushButton(_("Create new Mecenas contract"))
        b.clicked.connect(lambda: self.plugin.switch_to(Create, self.wallet_name, None, self.manager))
        hbox.addWidget(b)
        b = QPushButton(_("Find existing Mecenas contract"))
        b.clicked.connect(self.handle_finding)
        hbox.addWidget(b)
        vbox.addStretch(1)

    def handle_finding(self):
        self.contract_tuple_list = find_contract_in_wallet(self.wallet, MecenasContract)
        if len(self.contract_tuple_list):
            self.start_manager()
        else:
            self.show_error("You are not a party in any contract yet.")


    def start_manager(self):
        try:
            keypairs, public_keys = self.get_keypairs_for_contracts(self.contract_tuple_list)
            self.manager = ContractManager(self.contract_tuple_list, keypairs, public_keys, self.wallet)
            self.plugin.switch_to(Manage, self.wallet_name, self.password, self.manager)
        except Exception as es:
            print(es)
            # self.show_error("Wrong password.")
            self.plugin.switch_to(Intro,self.wallet_name,None,None)

    def get_keypairs_for_contracts(self, contract_tuple_list):
        if self.wallet.has_password():
            self.main_window.show_error(_(
                "Contract found! Plugin requires password to operate. It will get access to your private keys."))
            self.password = self.main_window.password_dialog()
            if not self.password:
                return
            try:
                self.wallet.keystore.get_private_key((True,0), self.password)
            except:
                self.show_error("Wrong password.")
                return
        keypairs = dict()
        public_keys=[]
        for t in contract_tuple_list:
            public_keys.append(dict())
            for m in t[MODE]:
                my_address=t[CONTRACT].addresses[m]
                i = self.wallet.get_address_index(my_address)
                if not self.wallet.is_watching_only():
                    priv = self.wallet.keystore.get_private_key(i, self.password)
                else:
                    print("watch only")
                    priv = None
                try:
                    if isinstance(self.wallet, ImportedPrivkeyWallet):
                        public = [self.wallet.keystore.address_to_pubkey(my_address).to_ui_string()]
                    else:
                        public = self.wallet.get_public_keys(my_address)
                    public_keys[contract_tuple_list.index(t)][m]=public[0]
                    keypairs[public[0]] = priv
                except Exception as ex:
                    print(ex)
        return keypairs, public_keys

class AdvancedWid(QWidget):
    toggle_sig = pyqtSignal()
    def __init__(self, parent):
        QWidget.__init__(self, parent)
        vbox = QVBoxLayout(self)
        hbox = QHBoxLayout()
        l = QLabel("<b> %s </b>" % "Advanced options")
        vbox.addWidget(l)
        self.nothing = QRadioButton("Mecenas contract v1.1 ")
        self.nothing.option = 1
        self.nothing.setChecked(True)
        self.nothing.toggled.connect(self.onClick)
        vbox.addWidget(self.nothing)
        self.escrow_address = QLineEdit()
        self.escrow_address.setPlaceholderText("Escrow bchaddress")
        self.no_opt_out_check = QRadioButton("Mecenas can terminate the contract only if protege won't claim the money for a month.")
        self.no_opt_out_check.option = 2
        self.no_opt_out_check.toggled.connect(self.onClick)
        vbox.addWidget(self.no_opt_out_check)
        self.esc_check = QRadioButton("Add escrow:")
        self.esc_check.option = 3
        self.esc_check.toggled.connect(self.onClick)
        self.escrow_address.setDisabled(True)
        self.escrow_address.textEdited.connect(self.toggle_sig.emit)
        vbox.addWidget(self.no_opt_out_check)
        self.legacy = QRadioButton("Legacy version (recipient has a plugin version below 1.2)")
        self.legacy.option = 4
        self.legacy.toggled.connect(self.onClick)
        vbox.addLayout(hbox)
        hbox.addWidget(self.esc_check)
        hbox.addWidget(self.escrow_address)
        vbox.addWidget(self.legacy)
        self.option = 1

    def onClick(self):
        radio = self.sender()
        self.option = radio.option
        self.escrow_address.setDisabled(not self.esc_check.isChecked())
        self.toggle_sig.emit()




class Create(QDialog, MessageBoxMixin):

    def __init__(self, parent, plugin, wallet_name, password, manager):
        QDialog.__init__(self, parent)
        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.password=None
        self.contract=None
        self.version=1
        if self.wallet.has_password():
            self.main_window.show_error(_(
                "Plugin requires password. It will get access to your private keys."))
            self.password = parent.password_dialog()
            if not self.password:
                print("no password")
                self.plugin.switch_to(Intro, self.wallet_name,None, None)
        self.fund_domain = None
        self.fund_change_address = None
        self.mecenas_address = self.wallet.get_unused_address()
        self.protege_address=None
        self.escrow_address=None
        self.addresses=[]
        self.total_value=0
        self.rpayment_value=0
        self.rpayment_time=0
        self.reps=0
        index = self.wallet.get_address_index(self.mecenas_address)
        key = self.wallet.keystore.get_private_key(index,self.password)
        self.privkey = int.from_bytes(key[0], 'big')

        if isinstance(self.wallet, Multisig_Wallet):
            self.main_window.show_error(
                "Mecenas is designed for single signature wallet only right now")

        vbox = QVBoxLayout()
        self.setLayout(vbox)
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        l = QLabel("<b>%s</b>" % (_("Creatin Mecenas contract:")))
        hbox.addWidget(l)
        hbox.addStretch(1)
        b = QPushButton(_("Home"))
        b.clicked.connect(lambda: self.plugin.switch_to(Intro, self.wallet_name, None, None))
        hbox.addWidget(b)
        l = QLabel(_("Redeem address") + ": auto (this wallet)")  # self.refreshing_address.to_ui_string())
        vbox.addWidget(l)





        l = QLabel(_("Protege address: "))
        vbox.addWidget(l)



        self.protege_address_wid = QLineEdit()
        self.protege_address_wid.textEdited.connect(self.mecenate_info_changed)
        vbox.addWidget(self.protege_address_wid)



        grid = QGridLayout()
        vbox.addLayout(grid)

        l = QLabel(_("Recurring payment value: "))
        grid.addWidget(l, 0, 0)
        l = QLabel(_("Repetitions:"))
        grid.addWidget(l, 0, 1)

        l = QLabel(_("Period (days): "))
        grid.addWidget(l, 0, 2)

        self.rpayment_value_wid = BTCAmountEdit(self.main_window.get_decimal_point)
        self.rpayment_value_wid.setAmount(1000000)
        self.rpayment_value_wid.textEdited.connect(self.mecenate_info_changed)

        self.repetitions = QLineEdit()
        self.repetitions.textEdited.connect(self.mecenate_info_changed)
        grid.addWidget(self.repetitions, 1, 1)

        self.rpayment_time_wid = QLineEdit()
        self.rpayment_time_wid.setText("30")
        self.rpayment_time_wid.textEdited.connect(self.mecenate_info_changed)
        grid.addWidget(self.rpayment_value_wid,1,0)
        grid.addWidget(self.rpayment_time_wid,1,2)
        grid.addWidget(QLabel("Total contract value:"),2,0)
        self.total_label = QLabel("0")
        hbox = QHBoxLayout()
        hbox.addWidget(self.total_label)
        hbox.addStretch(1)
        hbox.addWidget(QLabel("Total time:"))
        #grid.addWidget(self.total_label,2,1)
        grid.addLayout(hbox,2,1)
        self.total_time_label = QLabel("0")
        grid.addWidget(self.total_time_label,2,2)
        self.advanced_wid = AdvancedWid(self)
        self.advanced_wid.toggle_sig.connect(self.mecenate_info_changed)
        vbox.addWidget(self.advanced_wid)
        b = QPushButton(_("Create Mecenas Contract"))
        b.clicked.connect(self.create_mecenat)
        vbox.addStretch(1)
        vbox.addWidget(b)
        self.create_button = b
        self.create_button.setDisabled(True)
        vbox.addStretch(1)


    def mecenate_info_changed(self, ):
            # if any of the txid/out#/value changes
        try:
            self.protege_address = Address.from_string(self.protege_address_wid.text())
            self.reps = int(self.repetitions.text())
            self.rpayment_time = int(self.rpayment_time_wid.text())*3600*24//512
            self.rpayment_value = self.rpayment_value_wid.get_amount()
            total_time = int(self.rpayment_time_wid.text()) * self.reps
            self.total_time_label.setText("<b>%s</b>" % (str(total_time) + " days" ))

            if self.advanced_wid.option == 2:
                self.version = 2
                self.addresses = [self.protege_address, self.mecenas_address]
            elif self.advanced_wid.option == 3:
                self.version = 3
                self.escrow_address = Address.from_string(self.advanced_wid.escrow_address.text())
                self.addresses = [self.protege_address, self.mecenas_address, self.escrow_address]
            elif self.advanced_wid.option == 1:
                self.version = 1.1
                self.addresses = [self.protege_address, self.mecenas_address]
            elif self.advanced_wid.option == 4:
                self.version = 1
                self.addresses = [self.protege_address, self.mecenas_address]
            self.total_value = self.reps * (self.rpayment_value + MecenasContract.fee(self.version))
            self.total_label.setText(
                    "<b>%s</b>" % (
                                self.main_window.format_amount(self.total_value) + " " + self.main_window.base_unit()))

        except Exception as e:
            self.create_button.setDisabled(True)
            print(e)
        else:
            self.create_button.setDisabled(False)
            # PROTEGE is 0, MECENAS is 1
            self.contract = MecenasContract(self.addresses, v=self.version, data=[self.rpayment_time, self.rpayment_value])


    def build_otputs(self):
        outputs = []
        # convention used everywhere else in this plugin is is 0 for protege and 1 for mecenas
        # but I did it upside down here by mistake
        outputs.append((TYPE_SCRIPT, ScriptOutput(self.contract.op_return),0))
        for a in self.addresses:
            outputs.append((TYPE_ADDRESS, a, 546))
        outputs.append((TYPE_ADDRESS, self.contract.address, self.total_value))
        return outputs


    def create_mecenat(self, ):
        if self.total_value >= 2100000000:
            self.show_error("Contract total value shouldn't be larger than 21 BCH")
            return
        if self.contract.version == 3:
            receiver_is_mine = self.wallet.is_mine(self.contract.addresses[0])
            escrow_is_mine = self.wallet.is_mine(self.contract.addresses[2])
            if receiver_is_mine and escrow_is_mine:
                self.show_error("All three participants are in your wallet. Such contract will be impossible to terminate. Aborting.")
                return
        yorn = self.main_window.question(_(
            "Do you wish to create the Mecenas Contract?"))
        if not yorn:
            return
        outputs = self.build_otputs()
        try:
            tx = self.wallet.mktx(outputs, self.password, self.config,
                                  domain=self.fund_domain, change_addr=self.fund_change_address)
        except NotEnoughFunds:
            return self.show_critical(_("Not enough balance to fund smart contract."))
        except Exception as e:
            return self.show_critical(repr(e))
        tx.version=2
        try:
            self.main_window.network.broadcast_transaction2(tx)
            #show_transaction(tx, self.main_window, "Create Contract", prompt_if_unsaved=True)
        except:
            pass
        self.create_button.setText("Creating Mecenas Contract...")
        self.create_button.setDisabled(True)
        self.plugin.switch_to(Intro, self.wallet_name, None, None)



class ContractTree(MessageBoxMixin, PrintError, MyTreeWidget):
    update_sig = pyqtSignal()

    def __init__(self, parent, contracts):
        MyTreeWidget.__init__(self, parent, self.create_menu,[
            _('Contract address'),
            _('Pledge available in: '),
            _('Amount'),
            _('Recurring value'),
            _('My role'),
            _('Version')],stretch_column=0, deferred_updates=True)
        self.contract_tuple_list = contracts
        self.monospace_font = QFont(MONOSPACE_FONT)

        self.main_window = parent
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSortingEnabled(True)
        self.update_sig.connect(self.update)
        self.timer = QTimer(self)
        self.timer.setSingleShot(False)
        self.timer.timeout.connect(self.update_sig)
        #self.timer.start(2000)

    def create_menu(self, position):
        pass

    def get_selected_id(self):
        utxo = self.currentItem().data(0, Qt.UserRole)
        contract_tuple = self.currentItem().data(1, Qt.UserRole)
        m = self.currentItem().data(2, Qt.UserRole)
        if utxo == None:
            index = -1
        else:
            index = contract_tuple[UTXO].index(utxo)
        return contract_tuple, index, m

    def on_update(self):
        self.clear()
        # if len(self.contracts) == 1 and len(self.contracts[0][UTXO])==1:
        #     x = self.contracts[0][UTXO][0]
        #     item = self.add_item(x, self, self.contracts[0],self.contracts[0][MODE][0])
        #     self.setCurrentItem(item)
        # else:
        for t in self.contract_tuple_list:
            for m in t[MODE]:
                ver = str(t[CONTRACT].version)
                a = 0
                for u in t[UTXO]:
                    a+= u.get('value')
                amount = self.parent.format_amount(a, is_diff=False, whitespaces=True)
                value = self.parent.format_amount(len(t[UTXO])*t[CONTRACT].rpayment, is_diff=False, whitespaces=True)
                contract = QTreeWidgetItem([t[CONTRACT].address.to_ui_string(),'',"Total: " + amount,"Total: " + value,role_name(m),ver])
                contract.setData(1, Qt.UserRole, t)
                contract.setData(2,Qt.UserRole, m)
                contract.setFont(0, self.monospace_font)
                contract.setTextAlignment(2, Qt.AlignRight)
                contract.setTextAlignment(3, Qt.AlignRight)
                self.addChild(contract)
                for u in t[UTXO]:
                    item = self.add_item(u, contract, t, m)
                    self.setCurrentItem(item)
        self.sortByColumn(4, Qt.SortOrder.DescendingOrder)



    def add_item(self, u, parent_item, t, m):
        expiration = self.estimate_expiration(u, t)
        amount = self.parent.format_amount(u.get('value'), is_diff=False, whitespaces=True)
        value = self.parent.format_amount(t[CONTRACT].rpayment, is_diff=False, whitespaces=True)
        mode = role_name(m)
        utxo_item = SortableTreeWidgetItem([u['tx_hash'] , expiration, amount, value, '', ''])
        utxo_item.setData(0, Qt.UserRole, u)
        utxo_item.setData(1, Qt.UserRole, t)
        utxo_item.setData(2, Qt.UserRole, m)
        utxo_item.setTextAlignment(2, Qt.AlignRight)
        utxo_item.setTextAlignment(3, Qt.AlignRight)

        parent_item.addChild(utxo_item)
        return utxo_item


    def get_age(self, entry):
        txHeight = entry.get("height")
        currentHeight=self.main_window.network.get_local_height()
        age = (currentHeight-txHeight)//6
        return age

    def estimate_expiration(self, entry, ctuple):
        """estimates age of the utxo in days. There are 144 blocks per day on average"""
        txHeight = entry.get("height")
        age = self.get_age(entry)
        contract_i_time=ceil((ctuple[CONTRACT].i_time * 512) / (3600))
        if txHeight==0 :
            label = _("Waiting for confirmation.")
        elif (contract_i_time-age) >= 0:
            label = '{0:.2f}'.format((contract_i_time - age)/24) +" days"
        else :
            label = _("Pledge can be taken.")
        return label



class Manage(QDialog, MessageBoxMixin):
    def __init__(self, parent, plugin, wallet_name, password, manager):
        QDialog.__init__(self, parent)
        self.password=password

        self.main_window = parent
        self.wallet=parent.wallet
        self.plugin = plugin
        self.wallet_name = wallet_name
        self.config = parent.config
        self.complete = None
        self.manager=manager
        vbox = QVBoxLayout()
        self.setLayout(vbox)
        self.fee=1000
        self.contract_tree = ContractTree(self.main_window, self.manager.contract_tuple_list)
        self.contract_tree.on_update()
        vbox.addWidget(self.contract_tree)
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        vbox.addLayout(hbox)
        b = QPushButton(_("Home"))
        b.clicked.connect(lambda: self.plugin.switch_to(Intro, self.wallet_name, None, None))
        hbox.addWidget(b)
        b = QPushButton(_("Create new Mecenas Contract"))
        b.clicked.connect(lambda: self.plugin.switch_to(Create, self.wallet_name, None, self.manager))
        hbox.addWidget(b)
        vbox.addStretch(1)
        self.load_button = QPushButton(_("Load and sign termination tx"))
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addStretch(1)
        hbox.addWidget(self.load_button)
        self.load_button.clicked.connect(self.on_load)
        self.end_button = QPushButton( _("Terminate contract"))
        self.end_button.clicked.connect(self.end)
        self.pledge_button = QPushButton(_("Take payment from pledge"))
        self.pledge_button.clicked.connect(self.pledge)
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addWidget(self.end_button)
        hbox.addWidget(self.pledge_button)
        self.contract_tree.currentItemChanged.connect(self.update_buttons)
        self.update_buttons()


    def update_buttons(self):
        contract, utxo_index, m = self.contract_tree.get_selected_id()
        self.manager.choice(contract, utxo_index, m)
        self.end_button.setDisabled(False)
        self.pledge_button.setDisabled(False)
        if m == PROTEGE and self.manager.version != 3:
            self.end_button.setDisabled(True)
        if m == MECENAS or m == ESCROW:
            self.pledge_button.setDisabled(True)

    def on_load(self):
        tx=None
        try:
            tx = self.main_window.read_tx_from_file(fileName=None)
        except SerializationError as e:
            self.show_critical(_("Electron Cash was unable to deserialize the transaction:") + "\n" + str(e))
        if tx:
            tx.raw = tx.serialize()
            inputs = tx.inputs()
            metadata = inputs[0]['scriptSig'].split('1234567890')
            sig = metadata[1]
            xpub = '0'+metadata[0].strip('0')
            addr1 = Address.from_pubkey(xpub)
            other_party_role = self.manager.contract.addresses.index(addr1)

            for inp in tx.inputs():
                for i, j in self.manager.txin[0].items():
                    inp[i]=j
                inp['pubkeys'] = inp['x_pubkeys'] # problems with signing without it
                inp['sequence'] = 0
                inp['signatures'] = [None]
            tx.raw = tx.serialize()
            self.manager.signtx(tx)
            #self.wallet.sign_transaction(tx, self.password)
            for inp in tx.inputs():
                print(inp['signatures'])
                inp['x_pubkeys'].append(xpub)
                inp['signatures'].append(sig)
                if self.manager.mode > other_party_role:
                    # sender key can be on any place but receiver has to be on the first and escrow has to be on the second.
                    # see mecenas_v3.spedn
                    inp['x_pubkeys'][0],inp['x_pubkeys'][1] = inp['x_pubkeys'][1],inp['x_pubkeys'][0]
                    inp['signatures'][0],inp['signatures'][1] = inp['signatures'][1],inp['signatures'][0]
                inp['num_sig'] = 2
            tx.raw = tx.serialize()
            complete = self.manager.complete_method("end")
            complete(tx)
            show_transaction(tx, self.main_window, "End Mecenas Contract", prompt_if_unsaved=True)


    def end(self):
        print("end")
        yorn=self.main_window.question(_(
                 "Do you wish to take the payment?"))
        if yorn:
            if self.manager.version == 3:
                inputs = self.manager.txin
                for i in inputs:
                    i['num_sig'] = 2
                    i['x_pubkeys'] = [self.manager.pubkeys[self.manager.contract_index][self.manager.mode]]
                tx = self.manager.end_tx(inputs)
                if not self.wallet.is_watching_only():
                    self.manager.signtx(tx)
                inputs = tx.inputs()[0]
                sig = inputs['signatures'][0]
                pk = inputs["x_pubkeys"][0]
                print('SIGNATURE', sig)
                inputs['scriptSig']=inputs['scriptSig'][:-(len(sig)+len(pk)+10)]+pk+'1234567890'+sig
                tx.raw = tx.serialize()
                print("ScriptPK", self.manager.script_pub_key)
                show_transaction(tx, self.main_window, "End Contract", prompt_if_unsaved=True)
                return
            else:
                try:
                    inputs = self.manager.txin
                    tx = self.manager.end_tx(inputs)
                    complete = self.manager.complete_method()
                    if not self.wallet.is_watching_only():
                        self.manager.signtx(tx)
                        complete(tx)
                    self.main_window.network.broadcast_transaction2(tx)
                except ServerErrorResponse as e:
                    bip68msg = 'the transaction was rejected by network rules.\n\nnon-BIP68-final (code 64)'
                    if bip68msg in e.server_msg['message']:
                        self.show_error("Not ready yet!")
                    else:
                        self.show_error(e.server_msg)

    def pledge(self):
        if self.manager.chosen_utxo >= 0:
            yorn=self.main_window.question(_(
                 "Do you wish to take the payment?"))
            if yorn:

                tx = self.manager.pledge_tx()
                complete = self.manager.complete_method()
                if not self.wallet.is_watching_only():
                    self.manager.signtx(tx)
                    complete(tx)
                if tx:
                    try:
                        self.main_window.network.broadcast_transaction2(tx)
                    # show_transaction(tx, self.main_window, "Claim pledge", prompt_if_unsaved=True)
                    except ServerErrorResponse as e:
                        bip68msg = 'the transaction was rejected by network rules.\n\nnon-BIP68-final (code 64)'
                        if bip68msg in e.server_msg['message']:
                            self.show_error("Not ready yet!")
                        else:
                            self.show_error(e.server_msg)
                return
            else:
                return
        else:
            yorn=self.main_window.question(_("Do you wish to take the payment?"))
            if yorn:
                contract, utxo_index, m = self.contract_tree.get_selected_id()
                utxos = contract[UTXO]
                for u in range(len(utxos)):
                    self.manager.choice(contract, u, m)
                    tx = self.manager.pledge_tx()
                    complete = self.manager.complete_method()
                    if not self.wallet.is_watching_only():
                        self.manager.signtx(tx)
                        complete(tx)
                    if tx:
                        try:
                            self.main_window.network.broadcast_transaction2(tx)
                        except ServerErrorResponse as e:
                            bip68msg = 'the transaction was rejected by network rules.\n\nnon-BIP68-final (code 64)'
                            if bip68msg in e.server_msg['message']:
                                self.show_error("Not ready yet!")
                            else:
                                self.show_error(e.server_msg)
                       # show_transaction(tx, self.main_window, "Refresh entry", prompt_if_unsaved=True)
        self.plugin.switch_to(Manage, self.wallet_name, None, None)



def role_name(i):
    if i == PROTEGE:
        return "Protege"
    elif i == MECENAS:
        return "Mecenas"
    elif i == ESCROW:
        return "Escrow"
    else:
        return "unknown role"
