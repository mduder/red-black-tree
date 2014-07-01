""" Red-Black Tree and associated Node based on the CLRS specification

mduder.net
February 2014

Classes:
    Node -- Construct with Red-Black and general Binary Search Tree node properties

    Tree -- Construct supporting common Binary Search Tree methods
            This tree is NOT performant.  The implementation goal
            is to minimize lines of code and maximize readibility.
"""
from __future__ import print_function
import random

(RED, BLACK), (LEFT, RIGHT), (_REPORTED, _ACTUAL) = range(2), range(2), range(2)
(TREE_INSERT, TREE_DELETE, TREE_UPDATE)           = range(3)
(PRE_ORDER, IN_ORDER, POST_ORDER)                 = range(3)
(LOWEST_KEY, HIGHEST_KEY)                         = range(2)


class Node(object):
    """ Container for a key and it's associated meta-data

    Instance variables:
    key -- The integer-based value used for comparing against other nodes
                existing in a given Tree for locating values and positions.

    color -- The node property which a Red-Black tree leverages, binding
                its height to O(log(n)) where n is the tree node count.

    parent -- The alias to a node's direct ancestor.  This allows for simple
                path tracing during tree traversal.  An alternative to using
                parent aliases would be to store the path walked in a stack.

    child -- A pair of aliases to the node's direct descendants.

    Interfaces:
    compare -- This class method will compare the keys of two nodes
                (passed as arguments) and return the direction of the node
                with the lower value.

    is_nil -- Per CLRS spec, Nil nodes contain no value, no children, and
                are guaranteed to be black.  This helper method was introduced
                to abstract the check out from the Tree methods (algorithms).
    """

    @classmethod
    def compare(cls, n1, n2):
        if not isinstance(n1, Node) or not isinstance(n2, Node):
            raise TypeError
        elif n1.key is None or n2.key is None:
            raise KeyError
        elif n1.key < n2.key:
            return LEFT
        elif n1.key > n2.key:
            return RIGHT
        else:
            return None

    def __init__(self, key, value = None, nil = False):
        self.parent = None
        self.key = key
        if value:
            self.value = value

        if nil:
            self.color = BLACK
            self.child = [None, None]
        else:
            self.color = RED
            self.child = [Node(None, None, True),
                            Node(None, None, True)]
            self.child[LEFT].parent = self
            self.child[RIGHT].parent = self

    def is_nil(self):
        if self.child == [None, None]:
            return True
        return False


class Tree(object):
    """ Binary Search Tree leveraging colored nodes for binding tree height

    Instance variables:
    debug    -- When set as True at object initialization, extra tracking
                data is stored which allows future 'validate' method calls
                on the tree to inspect the tree's structure and elements.

    Interfaces:
    find     -- Given an integer value, retrieve the associated node.

    insert   -- Instantiate a Node object with the given integer value. Insert
                this node at the correct location in the tree, then re-balance
                the tree as necessary to maintain a height of O(log(n)).

    delete   -- Locate the Node object associated with the given integer value.
                Remove this node from the tree, then re-balance the tree
                as necessary to maintain a height of O(log(n)).

    validate -- This utility method verifies its associated tree's correctness.
                This will need to be called explicitly after any insert or delete.
                This will only run if the tree was initialized with debug=True.

    display  -- This utility method displays an in-order traversal of the tree.
                Each node will be represented by a three-value list, containing
                the node's value, the node's depth, and the node's color.

    update   -- Given an existing key in the tree, update its value.

    boundary -- Return the value of either lowest or highest key (as specified).

    traverse -- Given a callback (and optional process order), traverse the tree
                and invoke the callback once for each node.
    """

    def __init__(self, debug = False):
        self.__root = None
        self.__debug = debug
        if debug:
            self.__vals = {}
            self.__max_nodes = [0, 0]

    def __rotate(self, nFocus, _OBVERSE_DIRECTION):
        _REVERSE_DIRECTION = 1 - _OBVERSE_DIRECTION
        nChild = nFocus.child[_REVERSE_DIRECTION]
        nFocus.child[_REVERSE_DIRECTION] = nChild.child[_OBVERSE_DIRECTION]
        if nChild.child[_OBVERSE_DIRECTION]:
            nChild.child[_OBVERSE_DIRECTION].parent = nFocus
        nChild.parent = nFocus.parent
        if not nFocus.parent:
            self.__root = nChild
        else:
            _DIRECTION_FROM_PARENT = nFocus.parent.child.index(nFocus)
            nFocus.parent.child[_DIRECTION_FROM_PARENT] = nChild
        nChild.child[_OBVERSE_DIRECTION] = nFocus
        nFocus.parent = nChild

    def find(self, key, _post_action = None):
        if not isinstance(key, int):
            raise TypeError
        elif not self.__root:
            raise LookupError

        nFocus = self.__root
        _DIRECTION = None
        while not nFocus.is_nil():
            _DIRECTION = Node.compare(Node(key), nFocus)
            if _DIRECTION not in (LEFT, RIGHT):
                break
            nFocus = nFocus.child[_DIRECTION]
        if not nFocus.is_nil() and _post_action == TREE_INSERT:
            raise LookupError
        elif nFocus.is_nil() and _post_action != TREE_INSERT:
            raise LookupError
        return nFocus

    def insert(self, key, value = None):
        if not isinstance(key, int):
            raise TypeError
        nNew = Node(key, value)
        if not self.__root:
            nNew.color = BLACK
            self.__root = nNew
            return

        nFocus = self.find(key, TREE_INSERT)
        nNew.parent = nFocus.parent
        _DIRECTION = nFocus.parent.child.index(nFocus)
        nFocus.parent.child[_DIRECTION] = nNew
        self.__insert_fixup(nNew)

    def __insert_fixup(self, nFocus):
        while nFocus.parent and nFocus.parent.color == RED:
            nParent, nGrandpa = nFocus.parent, nFocus.parent.parent
            _DIRECTION_FROM_GRANDPA = nGrandpa.child.index(nParent)
            _OPPOSITE_DIRECTION = 1 - _DIRECTION_FROM_GRANDPA
            nUncle = nGrandpa.child[_OPPOSITE_DIRECTION]

            if nUncle.color == RED:
                # CLRS Case 1
                nParent.color, nUncle.color, nGrandpa.color = BLACK, BLACK, RED
                nFocus = nGrandpa
                continue

            if nParent.child[_OPPOSITE_DIRECTION] is nFocus:
                # CLRS Case 2
                nFocus = nFocus.parent
                self.__rotate(nFocus, _DIRECTION_FROM_GRANDPA)
                nParent, nGrandpa = nFocus.parent, nFocus.parent.parent # re-alias

            # CLRS Case 3
            nParent.color, nGrandpa.color = BLACK, RED
            self.__rotate(nGrandpa, _OPPOSITE_DIRECTION)
        self.__root.color = BLACK

    def delete(self, key):
        nFocus = self.find(key, TREE_DELETE)

        # Locate next-largest value as successor
        nReplacer = nFocus
        if not nFocus.child[LEFT].is_nil() and not nFocus.child[RIGHT].is_nil():
            nReplacer = nFocus.child[RIGHT]
            while not nReplacer.child[LEFT].is_nil():
                nReplacer = nReplacer.child[LEFT]

        # Extract replacer node from tree and copy its key to focus
        if not nReplacer.child[LEFT].is_nil():
            nRepChild = nReplacer.child[LEFT]
        else:
            nRepChild = nReplacer.child[RIGHT]
        nRepChild.parent = nReplacer.parent
        if nReplacer == self.__root:
            if nRepChild.is_nil():
                self.__root = None
            else:
                self.__root = nRepChild
                nRepChild.color = BLACK
            return

        nReplacer.parent.child[nReplacer.parent.child.index(nReplacer)] = nRepChild
        nFocus.key = nReplacer.key
        if nReplacer.color == BLACK:
            self.__delete_fixup(nRepChild)

    def __delete_fixup(self, nFocus):
        while nFocus is not self.__root and nFocus.color == BLACK:
            nParent = nFocus.parent
            _DIRECTION_FROM_PARENT = nParent.child.index(nFocus)
            _OPPOSITE_DIRECTION = 1 - _DIRECTION_FROM_PARENT
            nSibling = nParent.child[_OPPOSITE_DIRECTION]

            if nSibling.color == RED:
                # CLRS Case 1
                nSibling.color = BLACK
                nParent.color = RED
                self.__rotate(nParent, _DIRECTION_FROM_PARENT)
                nSibling = nParent.child[_OPPOSITE_DIRECTION] # re-alias

            if nSibling.child[LEFT].color == BLACK and \
                    nSibling.child[RIGHT].color == BLACK:
                # CLRS Case 2
                nSibling.color = RED
                nFocus = nParent
                continue

            if nSibling.child[_OPPOSITE_DIRECTION].color == BLACK:
                # CLRS Case 3
                nSibling.child[_DIRECTION_FROM_PARENT].color = BLACK
                nSibling.color = RED
                self.__rotate(nSibling, _OPPOSITE_DIRECTION)
                nSibling = nParent.child[_OPPOSITE_DIRECTION] # re-alias

            # CLRS Case 4
            nSibling.child[_OPPOSITE_DIRECTION].color = BLACK
            nSibling.color = nParent.color
            nParent.color = BLACK
            self.__rotate(nParent, _DIRECTION_FROM_PARENT)
            nFocus = self.__root
        nFocus.color = BLACK

    def update(self, key, value):
        node = self.find(key, TREE_UPDATE)
        node.value = value

    def boundary(self, find_option):
        if not self.__root:
            return None
        elif find_option is LOWEST_KEY:
            direction = LEFT
        elif find_option is HIGHEST_KEY:
            direction = RIGHT
        else:
            raise KeyError

        curr, prev = self.__root, None
        while curr:
            prev = curr
            curr = curr.child[direction]
        return prev

    def traverse(self, callback, process_order = IN_ORDER):
        if not self.__root:
            return
        curr, prev = self.__root, None
        depth = 0

        while curr:
            if not prev or curr in prev.child:
                depth += 1
                prev = curr

                if process_order is PRE_ORDER:
                    callback(curr, depth)
                if not curr.child[LEFT].is_nil():
                    curr = curr.child[LEFT]
                    continue

                if process_order is IN_ORDER:
                    callback(curr, depth)
                if not curr.child[RIGHT].is_nil():
                    curr = curr.child[RIGHT]
                    continue

                if process_order is POST_ORDER:
                    callback(curr, depth)
                curr = curr.parent

            elif prev is curr.child[LEFT]:
                depth -= 1
                prev = curr

                if process_order is IN_ORDER:
                    callback(curr, depth)
                if not curr.child[RIGHT].is_nil():
                    curr = curr.child[RIGHT]
                    continue

                if process_order is POST_ORDER:
                    callback(curr, depth)
                curr = curr.parent

            elif prev is curr.child[RIGHT]:
                depth -= 1
                prev = curr

                if process_order is POST_ORDER:
                    callback(curr, depth)
                curr = curr.parent

    def __inspect(self, nFocus):
        black_height = [0, 0]
        if nFocus.is_nil():
            return 1

        self.__max_nodes[_ACTUAL] += 1
        if nFocus.key in self.__vals.keys():
            print('Infinite cycle beginning at val:', nFocus.key)
            raise ReferenceError
        self.__vals[nFocus.key] = 0

        if not nFocus.child[LEFT].is_nil():
            if nFocus.color == RED and nFocus.child[LEFT].color == RED:
                print('Left child and focus both red at val:', nFocus.key)
                raise ValueError
            elif Node.compare(nFocus, nFocus.child[LEFT]) is LEFT:
                print('Left child value out of order at val:', nFocus.key)
                raise KeyError
        elif not nFocus.child[RIGHT].is_nil():
            if nFocus.color == RED and nFocus.child[RIGHT].color == RED:
                print('Right child and focus both red at val:', nFocus.key)
                raise ValueError
            elif Node.compare(nFocus, nFocus.child[RIGHT]) is RIGHT:
                print('Right child value out of order at val:', nFocus.key)
                raise KeyError

        black_height[LEFT] = self.__inspect(nFocus.child[LEFT])
        black_height[RIGHT] = self.__inspect(nFocus.child[RIGHT])
        if black_height[LEFT] > 0 and black_height[RIGHT] > 0 and \
                black_height[LEFT] != black_height[RIGHT]:
            print('Black height mismatch at children of val:', nFocus.key)
            raise ValueError

        if nFocus is self.__root and \
                self.__max_nodes[_REPORTED] != self.__max_nodes[_ACTUAL]:
            print('Node count mismatch, expected %d but found %d' %
                    (self.__max_nodes[_REPORTED], self.__max_nodes[_ACTUAL]))
            raise ArithmeticError

        if black_height[LEFT] == black_height[RIGHT] == 0:
            return 0
        elif nFocus.color == RED:
            return black_height[LEFT]
        else:
            return black_height[LEFT] + 1

    def validate(self, _pre_action = None):
        if not self.__debug or not self.__root:
            return
        self.__vals = {}
        self.__max_nodes[_ACTUAL] = 0
        if _pre_action == TREE_INSERT:
            self.__max_nodes[_REPORTED] += 1
        elif _pre_action == TREE_DELETE:
            self.__max_nodes[_REPORTED] -= 1
        self.__inspect(self.__root)

    def __display_cb(self, node, depth):
        if node.color == RED:
            self.__elem_list.append((node.key, depth, ' RED '))
        else:
            self.__elem_list.append((node.key, depth, 'BLACK'))

    def display(self):
        if not self.__root:
            return
        self.__elem_list = []
        self.traverse(self.__display_cb)
        print(self.__elem_list)
        self.__elem_list = None


# Sanity check the tree implementation with a large count of variant instances
def random_seed_tests():
    test_count = 42
    for seed in range(test_count):
        print('Testing seed:', seed)
        random.seed(seed)
        for count in range(1, test_count):
            rand_array = list(range(count))
            random.shuffle(rand_array)
            tree = Tree(debug = True)
            for key in rand_array:
                tree.insert(key)
                tree.validate(TREE_INSERT)
            for key in rand_array:
                tree.delete(key)
                tree.validate(TREE_DELETE)

# Running as main shall invoke random seed testing
if __name__ == '__main__':
    print('Init')
    random_seed_tests()
