from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import electroncash.web as web
import webbrowser
from .mecenas_contract import MecenasContract
from electroncash.address import ScriptOutput, OpCodes, Address
from electroncash.transaction import Transaction,TYPE_ADDRESS, TYPE_SCRIPT, SerializationError
from electroncash_gui.qt.amountedit  import BTCAmountEdit
from electroncash.i18n import _
from electroncash_gui.qt.util import *
from electroncash.wallet import Multisig_Wallet
from electroncash.util import NotEnoughFunds
from electroncash_gui.qt.transaction_dialog import show_transaction
from .contract_finder1 import find_contract_in_wallet
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
        self.nothing = QRadioButton("Mecenas v1.1 (recipient needs plugin version above 1.2)")
        self.nothing.option = 1
        self.nothing.setChecked(True)
        self.nothing.toggled.connect(self.onClick)
        vbox.addWidget(self.nothing)
        self.escrow_address = QLineEdit()
        self.escrow_address.setPlaceholderText("Escrow bchaddress")
        self.no_opt_out_check = QRadioButton("Mecenas can end the contract only if protege is inactive for a month.")
        self.no_opt_out_check.option = 2
        self.no_opt_out_check.toggled.connect(self.onClick)
        vbox.addWidget(self.no_opt_out_check)
        self.esc_check = QRadioButton("Add escrow:")
        self.esc_check.option = 3
        self.esc_check.toggled.connect(self.onClick)
        self.escrow_address.setDisabled(True)
        self.escrow_address.textEdited.connect(self.toggle_sig.emit)
        vbox.addWidget(self.no_opt_out_check)
        self.legacy = QRadioButton("Legacy version")
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
            reps = int(self.repetitions.text())
            self.rpayment_time = int(self.rpayment_time_wid.text())*3600*24//512
            self.rpayment_value = self.rpayment_value_wid.get_amount()
            self.total_value = reps*(self.rpayment_value + 1000)
            total_time = int(self.rpayment_time_wid.text()) * reps
            self.total_label.setText("<b>%s</b>" % (self.main_window.format_amount(self.total_value) + " " + self.main_window.base_unit()))
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
        except:
            self.create_button.setDisabled(True)
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
            _('My role')],stretch_column=0, deferred_updates=True)
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
                contract = QTreeWidgetItem([t[CONTRACT].address.to_ui_string(),'','','',role_name(m)])
                contract.setData(1, Qt.UserRole, t)
                contract.setData(2,Qt.UserRole, m)
                self.addChild(contract)
                for u in t[UTXO]:
                    item = self.add_item(u, contract, t, m)
                    self.setCurrentItem(item)


    def add_item(self, u, parent_item, t, m):
        expiration = self.estimate_expiration(u, t)
        amount = self.parent.format_amount(u.get('value'), is_diff=False, whitespaces=True)
        value = self.parent.format_amount(t[CONTRACT].rpayment, is_diff=False, whitespaces=True)
        mode = role_name(m)
        utxo_item = SortableTreeWidgetItem([u['tx_hash'] , expiration, amount, value, mode])
        utxo_item.setData(0, Qt.UserRole, u)
        utxo_item.setData(1, Qt.UserRole, t)
        utxo_item.setData(2, Qt.UserRole, m)
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
        self.load_button = QPushButton(_("Load"))
        hbox = QHBoxLayout()
        vbox.addLayout(hbox)
        hbox.addStretch(1)
        hbox.addWidget(self.load_button)
        self.load_button.clicked.connect(self.on_load)
        self.end_button = QPushButton( _("End"))
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
        try:
            tx = self.main_window.read_tx_from_file(fileName=None)
        except SerializationError as e:
            self.show_critical(_("Electron Cash was unable to deserialize the transaction:") + "\n" + str(e))
        if tx:
            for i in tx.inputs():
                i['x_pubkeys'].append(self.manager.pubkeys[self.manager.contract_index][self.manager.mode])
            self.manager.signtx(tx)
            self.show_transaction(tx)

    def tx_gen_end(self, inputs):
        outputs = [
            (TYPE_ADDRESS, self.manager.contract.addresses[self.manager.mode], self.manager.value)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        fee = len(tx.serialize(True)) // 2 + 1
        if fee > self.manager.value:
            self.show_error("Not enough funds to make the transaction!")
            return
        outputs = [
            (TYPE_ADDRESS, self.manager.contract.addresses[self.manager.mode], self.manager.value - fee)]
        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        return tx

    def end(self):
        print("end")
        self.complete = self.manager.complete_method("end")
        inputs = self.manager.txin
        tx = self.tx_gen_end(inputs)
        if self.manager.version == 3 and self.manager.mode == ESCROW:
            for i in inputs:
                i['num_sig'] = 2
                i['x_pubkeys'] = [self.manager.pubkeys[self.manager.contract_index][self.manager.mode]]
                tx = self.tx_gen_end(inputs)
                self.manager.signtx(tx)
                tx.raw = tx.serialize()
                show_transaction(tx, self.main_window, "End Mecenas Contract", prompt_if_unsaved=True)
                return
        # Mark style fee estimation
        if not self.wallet.is_watching_only():
            self.manager.signtx(tx)
            self.complete(tx)
        show_transaction(tx, self.main_window, "End Mecenas Contract", prompt_if_unsaved=True)
        self.plugin.switch_to(Manage, self.wallet_name, None, None)

    def pledge(self):
        self.complete = self.manager.complete_method()
        inputs = self.manager.txin
        # Mark style fee estimation
        outputs = [
            (TYPE_ADDRESS, self.manager.contract.address, self.manager.value - self.fee - self.manager.rpayment),
            (TYPE_ADDRESS, self.manager.contract.addresses[self.manager.mode], self.manager.rpayment)        ]

        tx = Transaction.from_io(inputs, outputs, locktime=0)
        tx.version = 2
        #print(tx.outputs())
        if not self.wallet.is_watching_only():
            self.manager.signtx(tx)
            self.complete(tx)
        show_transaction(tx, self.main_window, "Pledge", prompt_if_unsaved=True)
        self.plugin.switch_to(Manage, self.wallet_name, None, None)

    def save(self, tx):
        name = 'signed_%s.txn' % (tx.txid()[0:8]) if tx.is_complete() else 'unsigned.txn'
        fileName = self.main_window.getSaveFileName(_("Select where to save your signed transaction"), name, "*.txn")
        if fileName:
            tx_dict = tx.as_dict()
            with open(fileName, "w+", encoding='utf-8') as f:
                f.write(json.dumps(tx_dict, indent=4) + '\n')
            self.show_message(_("Transaction saved successfully"))
            self.saved = True

def role_name(i):
    if i == PROTEGE:
        return "Protege"
    elif i == MECENAS:
        return "Mecenas"
    elif i == ESCROW:
        return "Escrow"
    else:
        return "unknown role"
