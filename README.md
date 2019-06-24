# Mecenas - recurring payment smart contract plugin
Mecenas was created as **a solution** for bitcoin **patronate** exit scam risk. The plugin create and manage a contract that shifts the responsibility for making the transaction from the sender to the receiver with time and value restriction.

## Features:
* Made on **BCH** chain,
* Noncustodial,
* Permission-less,
* The smart contract based on **covenant**,
* The sender (called **mecenas**) sends BCH to a special contract address,
* Mecenas can access this money **any time**,
* The receiver (called **protege**) can withdraw **predefined amount** of BCH in predefined **time intervals** to a predefined address.
* Can be integrated with **other services**,
* In case the service **goes unresponsive**, the contract can be viewd and managed with Electron Cash plugin, **like nothing ever happened**.
* Parties may continue the contract, end it or prolong it.


## Quick start

1. First, download and verify sha256 of the mecenas-vVERSION.zip file from [relesases](). Then go to your Electron Cash and install the plugin,
2. The plugin tab should show up. Click "Create new Mecenas contract" if you want to become someone elses [mecenas](https://en.wikipedia.org/wiki/Gaius_Maecenas#Maecenate_(patronage)) or
3. click "Find existing Mecenas contract" if you already are in a mecenas-protege relationship.

### Creating
 1. Set protege **address**, **total amount** you want to put into the contract, the **value** of a single protege withdrawal and the minimum **time interval** between withdrawals,
 2. Hit "Create Mecenas Contract" button,
 3. Go to "Find existing Mecenas contract" to see the contract.

### Managing contracts.

1. You will see the list of the contracts you participate in. Each have a contract address, time left to withdrawal, total amount and your role in the contract,
2. If you click on contract address or entry under the contract address, the wide button below will change according to your role in the contract.

i.e.

* Button will show **End** if you are mecenas,
* Button will show **Take payment from the pledge** if you are protege.


## Contract details

### Smart contract basics
The contract is defined by a special address that is cryptographically determined by the contract itself. [Learn more](https://en.bitcoin.it/wiki/Pay_to_script_hash). Funds are "in the contract" when they are sent to this special address. 

A contract consists of challenges - requirements that have to be met to access the funds stored in it.


### Mecenas contract
Mecenas contract consists of the two challenges.
Pseudo-code below shows the idea behind it:
```
contract Mecenas()
{
    challenge protege()
    {
        verify if <time> have passed 
        since the money were put in the contract

        verify if the transaction 
        sends <amount> to the <protege address>
        and the rest of the funds
        back to the same contract address
    }
    
    challenge mecenas()
    {
        verify if the transaction 
        was signed by the creators wallet
     }

}
```
*protege* challenge measures time since the money were put on the contract and is locked for a predefined period. The action of taking payment from the pledge puts the remaining money back to the contract, effectively resetting the timer.

*mecenas* challenge let mecenas do whatever they want with the money.

Transaction fee for protege is 1000sat.

This creates a **recurring payment system**, that is not dependent on the payer being on-line, without necesity to deposit your funds to a third party. It can be used as a way to become a patron for your favorite creators, artists, developers. It can be also used as tool for any **subscribtion-based service** and **Licho vault**. 


## Advanced usage 

### Licho Vault

The contract can be used to strenghen security of your savings wallet. To make a **Licho vault**, create a Mecenas contract where your every-day wallet is **protege** and your savings wallet is **mecenas**. Set the single withdrawal value for the average amount you spend e.g. per week and the withdrawal interval for 7 days. This way, every time you transfer money from your savings to your every-day wallet you don't have to use a key to  your savings! If the every-day-use key get exposed you will lose one time withdrawal not all your savings. It's similar to a credit card daily limit. Remember that the rules apply per every coin in the contract, so if you add new money to it it will double the amount you can withdraw in a time period.

### Atomizing the contract
The rules of contract apply per [coin](https://en.bitcoin.it/wiki/Coin_analogy) in the contract. This feature can be used to take into account bitcoin price changes. Let's say Alice plans to become a mecenas of Bob and pay him $10 every week but she want it denominated in dollars. She creates a contract with $1 monthly pledge and puts 10 coins in it. Bob can access every coin once per month withdrawing 10 x $1. This way, if after some time the price of bitcoin grows, alice can withdraw a single coin to adjust for the price change. If the price doubles she withdraws  5 coins and Bob is left with monhly pledge that is still worth 10$. The precision is limited by the transation fees one is willing to pay. Every withdrawal costs 1000 sat/coin because of bitcoin network fees.

### Integrating with other services
The contract is designed to be integrated with other services in a non-custodial way. The service may add the funcionality for protege to share exclusive content with mecenases and relive protege from the duty of grabing the  recurring payments. It's possible to make noncustodial subscribtion based service with it. In case the service goes unresponsive, contract can be viewd and operated with Electron Cash plugin, like nothing ever happened. When the contract is created a [p2sh notification](https://gist.github.com/KarolTrzeszczkowski/3f7e719902e8d678efcc71875df66f21) is sent to the participants of the contract with OP_RETURN output. Outputs are sorted to make it easier to determine the role of participant. Mecenas dust output is first, protege output is second. Contract address is not changing when operating the contract.


## Disclaimer

The author of this software is not a party to a Last Will contract, have no control over it and cannot influence it's outcome. The author is not responsible for legal implications of the Last Will contract nor is competent to settle any disputes. The author is not responsible for the contract expected behavior.

## License

This software is distributed on GPL v2 license. The author encourage you to build your own smart contract plugins based on this plugin code, implement desired functions and submit a pull request to this repository or fork this project and compete, if I fail to deliver what you expect. Just remember to publish your improvements on the same license.

## Contact the author

With any problems contact me on telegram: **@licho92karol**, reddit: **u/Licho92** e-mail: **name.lastname@gmail.com**. If you wish to contact me via Signal or whatsapp, ask for my phone number on any of this channels.

## Mecenate and donations

If you wish to support development of the [Mecenas plugin](), [Last Will plugin](https://github.com/KarolTrzeszczkowski/Electron-Cash-Last-Will-Plugin), [Inter-Wallet transfer plugin](https://github.com/KarolTrzeszczkowski/Electron-Cash-Plugin-Template), consider **becoming my mecenas** for the address:

bitcoincash:qq93dq0j3uez8m995lrkx4a6n48j2fckfuwdaqeej2

I will prioritize my patrons feature requests, offer direct support in case of problems or support with integration in their services.

**Or donating**: 

Cash Account: Licho#14431

bitcoincash:qq93dq0j3uez8m995lrkx4a6n48j2fckfuwdaqeej2

Legacy format: 121dPy31QTsxAYUyGRbwEmW2c1hyZy1Xnz

![donate](/pictures/donate.png)






