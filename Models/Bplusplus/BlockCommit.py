from Scheduler import Scheduler
from InputsConfig import InputsConfig as p
from Models.Bplusplus.Node import Node
from Statistics import Statistics
from Models.Transaction import LightTransaction as LT, FullTransaction as FT
from Models.Network import Network
from Models.Bplusplus.Consensus import Consensus as c
from Models.BlockCommit import BlockCommit as BaseBlockCommit


class BlockCommit(BaseBlockCommit):

    # Handling and running Events
    def handle_event(event):
        if event.type == "create_block":
            BlockCommit.generate_block(event)
        elif event.type == "receive_block":
            BlockCommit.receive_block(event)

    # Block Creation Event
    def generate_block(event):
        miner = p.NODES[event.block.miner]
        new_branch = event.block
        miner_virtual_block = miner.blockchain[new_branch.depth]

        if new_branch.depth <= miner.last_finished_virtual_block().depth:
            return

        if miner_virtual_block.branches[new_branch.branch_id] != None:
            return

        Statistics.totalBlocks += 1  # count # of total blocks created!
        if p.hasTrans:
            if p.Ttechnique == "Light":
                blockTrans, blockSize = LT.execute_transactions()
            elif p.Ttechnique == "Full":
                blockTrans, blockSize = FT.execute_transactions(
                    miner, event.time)

            new_branch.transactions = blockTrans
            new_branch.usedgas = blockSize

        miner_virtual_block.set_branch(new_branch)
        BlockCommit.propagate_block(new_branch)
        BlockCommit.generate_next_block(miner, event.time)

        if p.hasTrans and p.Ttechnique == "Light":
            LT.create_transactions()  # generate transactions

    # Block Receiving Event
    def receive_block(event):
        receiver = p.NODES[event.node]
        new_branch = event.block
        receiver.grow_blockchain(new_branch.depth)
        receiver_virtual_block = receiver.blockchain[new_branch.depth]

        #### case 1: the id of received branch is never seen before ####
        if receiver_virtual_block.branches[new_branch.branch_id] == None:
            receiver_virtual_block.set_branch(new_branch)

            #### case 1.1: the received branch is also deeper than current deepest finished virtual block ####
            if new_branch.depth > receiver.last_finished_virtual_block().depth:
                BlockCommit.generate_next_block(receiver, event.time)

            if p.hasTrans and p.Ttechnique == "Full":
                BlockCommit.update_transactionsPool(receiver, new_branch)

    # Upon generating or receiving a block, the miner start working on the next block as in POW
    def generate_next_block(node, currentTime):
        if node.hashPower > 0:
            # time when miner x generate the next block
            blockTime = currentTime + c.Protocol(node)
            Scheduler.create_block_event(node, blockTime)

    def generate_initial_events():
        currentTime = 0
        for node in p.NODES:
            BlockCommit.generate_next_block(node, currentTime)

    def propagate_block(block):
        for recipient in p.NODES:
            if recipient.id != block.miner:
                # draw block propagation delay from a distribution !! or you can assign 0 to ignore block propagation delay
                blockDelay = Network.block_prop_delay()
                Scheduler.receive_block_event(recipient, block, blockDelay)