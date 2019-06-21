
from .mecenas_contract import MecenasContract
from electroncash.address import Address, ScriptOutput
from itertools import permutations, combinations


def find_contract(wallet):
    """Searching transactions for the one maching contract
    by creating contracts from outputs"""
    contracts=[]
    for hash, t in wallet.transactions.items():
        out = t.outputs()
        address = ''
        if len(out) > 2:
            address, v, data  = get_contract_info(out)
            if address is None or v is None or data is None:
                continue
            candidates = get_candidates(out)
            for c in candidates:
                mec = MecenasContract(c,t.as_dict(),v=v, data=data)
                if mec.address.to_ui_string() == address:
                        print("asking")
                        response = wallet.network.synchronous_get(
                            ("blockchain.scripthash.listunspent", [mec.address.to_scripthash_hex()]))
                        if unfunded_contract(response) : #skip unfunded and ended contracts
                            continue
                        contracts.append(( response, mec, find_my_role(c, wallet)))

    remove_duplicates(contracts)
    return contracts




def remove_duplicates(contracts):
    c = contracts
    for c1, c2 in combinations(contracts,2):
        if c1[1].address == c2[1].address:
            c.remove(c1)
    return c

def unfunded_contract(r):
    """Checks if the contract is funded"""
    s = False
    if len(r) == 0:
        s = True
    for t in r:
        if t.get('value') == 0: # when contract was drained by fees it's still in utxo
            s = True
    return s


def get_contract_info(outputs):
    """Finds p2sh output"""
    for o in outputs:
        try:
            assert isinstance(o[1], ScriptOutput)
            assert o[1].to_ui_string().split(",")[1] == " (4) '>sh\\x00'"
            a = o[1].to_ui_string().split("'")[3][:42]
            version = int(o[1].to_ui_string().split("'")[3][42:])
            data =[int(e) for e in o[1].to_ui_string().split("'")[5].split(' ')]
            print("Data: ")
            print(data)
            assert 0 <= version <= 1
            return Address.from_string(a).to_ui_string(), version, data
        except:
            continue
    return None, None, None



def get_candidates(outputs):
    """Creates all permutations of addresses that are not p2sh type"""
    candidates = []
    for o1, o2 in permutations(outputs, 2):
        if not (isinstance(o1[1], Address) and isinstance(o2[1], Address) ):
            continue
        if o1[1].kind or o2[1].kind :
            continue
        candidates.append([o1[1], o2[1]])
    return candidates

def find_my_role(candidates, wallet):
    """Returns my role in this contract. 0 is mecenas, 1 is protege"""
    roles=[]
    for counter, a in enumerate(candidates, start=0):
        if wallet.is_mine(a):
            roles.append(counter)
    if len(roles):
        return roles





