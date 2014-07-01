""" Cross-platform front-end for interaction and display of a Red-Black Tree

mduder.net
June 2014

(Non-empty) Classes:
    Node             -- Graphical representation of a red or black node in the tree.

    NodeValTextInput -- Text box for numerical user input which will be acted upon
                        after the user selects a button action to take on the value.

    NodeField        -- Canvas of drawn Nodes representing the tree's stored keys.
                        This field is horizontally scrollable on touch screens.

    TreeDisplay      -- App root which owns the button / text input menu, the
                        node field display and the tree back-end database.
"""
from kivy.app import App
from kivy.clock import Clock
from kivy.properties import ObjectProperty, BooleanProperty
from kivy.core.window import Window
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scatter import Scatter
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.vertex_instructions import Line
from kivy.graphics.context_instructions import Color

import kivy.metrics as k_met
import red_black_tree as rbt_ns

(POS_X, POS_Y) = range(2)

# Begin empty classes for cleaner kv syntax
class ActionButtonBase(Button):
    pass

class RedrawButton(ActionButtonBase):
    pass

class InsertButton(ActionButtonBase):
    pass

class DeleteButton(ActionButtonBase):
    pass

class ClearButton(ActionButtonBase):
    pass

class LandscapeMenu(BoxLayout):
    pass

class NodeFieldContainer(FloatLayout):
    pass
# End empty kv classes


class Node(Scatter):
    """ Graphical representation of a red or black node in the tree.

    A Node object will be generated for each key in the red-black tree.
    These exist only for the duration of the current canvas drawing and
    are not tied to the persistence of the red-black tree numeric keys
    which they represent.

    Class variable:
    radius -- A length unit used by the NodeField for determining canvas
              draw sizes and distances.  Note that Kivy requires
              class level properties for any canvas interface.
    """
    radius = 10

    def __init__(self, node_key = 0, node_color = rbt_ns.RED, **kwargs):
        self.node_key = node_key
        if node_color == rbt_ns.RED:
            self.canvas_color = (1, 0, 0, 1)
        elif node_color == rbt_ns.BLACK:
            self.canvas_color = (0, 0, 0, 1)
        super(Node, self).__init__(**kwargs)


class NodeValTextInput(TextInput):
    """ Text box which will store user input, consumed on button action taken.
    """
    def __init__(self, **kwargs):
        super(NodeValTextInput, self).__init__(**kwargs)
        self._async_init_trigger = Clock.create_trigger(self.__async__init__)
        self._async_init_trigger()

    # Async required to prevent user from engaging with the input before
    # all the parent / child relations have been instantiated.  The app
    # will crash if this is not done and the user is particularly fast.
    def __async__init__(self, time_elapsed):
        if not self.parent or not self.parent.parent:
            self._async_init_trigger()
            return
        self._async_init_trigger = None
        self.parent.parent.nv_ti = self

    # Oddly enough, Kivy passes self twice to this handler, and requires
    # calls to super() pass this second self as the first argument
    def on_focus(self, self_again, is_focused):
        if is_focused:
            self.parent.parent.buttons_locked = True
        else:
            self.parent.parent.buttons_locked = False
        return super(NodeValTextInput, self).on_focus(self_again, is_focused)


class NodeField(Scatter):
    """ Canvas manipulation widget, which calculates and redraws the visual
        representation of the tree with every user action taken.

        A NodeField object allows horizontal translation on touch-enabled devices
        by means of user swiping.  The drawn field persists only for the
        duration of the application

    Class variable / Interface:
    draw_action -- An event container which triggers redraw when modified.
                   Kivy requires properties be defined at the class level.
    """
    draw_action = ObjectProperty()

    def __init__(self, **kwargs):
        super(NodeField, self).__init__(**kwargs)
        self.bind(draw_action = self._draw_tree_on_canvas)
        self.origin = (self.get_center_x(), self.get_center_y())
        self.coords_valid = False
        self.rbt_draw_depth = 0
        self._async_init_trigger = Clock.create_trigger(self.__async__init__)
        self._async_init_trigger()

    # Async required to prevent user from engaging with the input before
    # all the parent / child relations have been instantiated
    def __async__init__(self, time_elapsed):
        if not self.parent or not self.parent.parent:
            self._async_init_trigger()
            return
        self._async_init_trigger = None
        self.parent.parent.rbt_nf = self
        self._poll_coords_trigger = Clock.create_trigger(self._poll_coords_handler)
        self._poll_coords_trigger()

    # This handler will be triggered once when the app is first started
    def _poll_coords_handler(self, time_elapsed):
        current_position = (self.get_center_x(), self.get_center_y())
        if current_position == self.origin:
            # No change yet, schedule again for next frame
            self._poll_coords_trigger()
            return
        self.origin = current_position
        self.coords_valid = True
        self._draw_tree_on_canvas(self, ('Redraw', False, 0))

    # This handler is called implicitly by the Kivy framework on user touch
    def on_touch_down(self, touch):
        # Fake the X axis position to 'enable' endless horizontal scrolling
        touch.push()
        touch.x = self.get_center_x()
        ret = super(NodeField, self).on_touch_down(touch)
        touch.pop()
        return ret

    # Oddly enough, Kivy passes self twice to this handler
    def _draw_tree_on_canvas(self, self_again, unused_object):
        self.clear_widgets()
        self.canvas.clear()

        # Must re-center the tree on every redraw because app re-orientation
        # events handled internally by Kivy force a widget level position
        # translation on the node field.  However since the field is a Scatter
        # widget, this translation is inherently broken, and a redrawn field
        # can end up drawn either off the screen, or over the buttons, or worse.
        self.set_center_x(self.origin[POS_X])
        self.set_center_y(self.origin[POS_Y])
        self.rbt_draw_depth = 0
        self.parent.parent.rbt_db.traverse(self._find_tree_depth, rbt_ns.IN_ORDER)
        self.parent.parent.rbt_db.traverse(self._draw_field_node, rbt_ns.PRE_ORDER)

    # This event will be called back from the tree traversal for each key.
    def _find_tree_depth(self, db_node, node_depth):
        if self.rbt_draw_depth < node_depth:
            self.rbt_draw_depth = node_depth

    # This event will be called back from the tree traversal for each key.
    # Kivy metrics are leveraged (as k_met) to keep distances relative to
    # the size of the device screen.
    #
    # TODO: Need to rescale the canvas drawing after nodes reach the screen edge.
    #       Must keep all the nodes on the screen vertically but can not allow
    #       the user to drag and scale field, as this will overlap with buttons.
    def _draw_field_node(self, db_node, node_depth):
        # First, calculate and store the X / Y coordinates of the Node
        if not db_node.parent:
            db_node.value = (self.get_center_x(),
                             self.get_center_y() + \
                             k_met.sp((self.rbt_draw_depth - 1) * 2 * Node.radius))
        else:
            if db_node is db_node.parent.child[rbt_ns.LEFT]:
                DIRECTION_INDICATOR = -1
            else:
                DIRECTION_INDICATOR = 1
            x_offset = 2 ** (self.rbt_draw_depth - node_depth - 1)
            x_position = db_node.parent.value[POS_X] + \
                    k_met.sp((2 * Node.radius * x_offset * DIRECTION_INDICATOR))
            y_position = db_node.parent.value[POS_Y] - \
                    k_met.sp((2 * 2 * Node.radius))
            db_node.value = (x_position, y_position)

        # Next, draw the graphical node onto the canvas using previous coordinates
        new_node = Node(db_node.key, db_node.color)
        new_node.set_center_x(db_node.value[POS_X])
        new_node.set_center_y(db_node.value[POS_Y])
        self.add_widget(new_node)
        if db_node.parent:
            with self.canvas:
                Color(0, 0, 1, 1)
                Line(points = [db_node.value[POS_X],
                               db_node.value[POS_Y] + k_met.sp(Node.radius),
                               db_node.parent.value[POS_X],
                               db_node.parent.value[POS_Y] - k_met.sp(Node.radius)])


class TreeDisplay(BoxLayout):
    """ Root app widget which re-arranges the menu based on app orientation.
        This also owns the node field manipulator and the back-end tree database.
    """
    def __init__(self):
        super(TreeDisplay, self).__init__()
        self.ui_locked = True
        self.buttons_locked = False
        self.action_id = 0
        self.rbt_db = rbt_ns.Tree()
        self.rbt_op = {'Redraw': lambda unused: None,
                       'Insert': self.rbt_db.insert,
                       'Delete': self.rbt_db.delete,
                       'Clear' : self.rbt_db.__init__}
        self.rbt_nf = None
        self.nv_ti = None
        self._comp_wait_trigger = Clock.create_trigger(self._comp_wait_handler)
        self._comp_wait_trigger()

    # This trigger will re-activate itself until the app components
    # are ready for user interaction.
    def _comp_wait_handler(self, time_elapsed):
        print 'Waiting for components'
        if not self.nv_ti or not self.rbt_nf or self.rbt_nf.coords_valid == False:
            print 'Components not ready'
            self._comp_wait_trigger()
            return
        self.ui_locked = False

    # This handler is called implicitly by the Kivy framework on user touch
    def on_touch_down(self, touch):
        if self.ui_locked:
            return True
        elif self.buttons_locked:
            return self.nv_ti.on_touch_down(touch)
        return super(TreeDisplay, self).on_touch_down(touch)

    # This method is invoked by buttons as indicated in the kv file.
    #
    # While never used, the action_id value is unfortunately required
    # in order to trigger the draw_action property event.  If any Kivy
    # event is triggered with an argument which does not differ from
    # the current object stored in the event repository, the handler is
    # *NOT* invoked.
    def button_press(self, input_option):
        self.action_id += 1
        if self.ui_locked:
            print 'user interface locked - will not %s' % (input_option)
            return
        elif not self.nv_ti:
            print 'TextInput not found - will not %s' % (input_option)
            return

        if input_option in ('Redraw', 'Clear'):
            self.rbt_op[input_option](None)
            self.rbt_nf.draw_action = (self.action_id)
            return

        try:
            key = int(self.nv_ti.text)
        except ValueError:
            print 'invalid input \'%s\' - will not %s' % \
                    (self.nv_ti.text, input_option)
            return
        if key < 1 or key > 999:
            print 'integer %s out of range - will not %s' % \
                    (self.nv_ti.text, input_option)
            return

        try:
            self.rbt_op[input_option](key)
        except LookupError:
            if input_option == 'Insert':
                print 'duplicate key found in tree - will not Insert'
            elif input_option == 'Delete':
                print 'key not found in tree - will not Delete'
            return
        self.rbt_nf.draw_action = (self.action_id)


class Tree_GUIApp(App):
    """ Application start-up handler.  This will set environmental parameters.
    """
    def build(self):
        Window.clearcolor = (1, 1, 1, 1)
        return TreeDisplay()

    def on_pause(self):
        return True

    def on_resume(self):
        pass


if __name__ == '__main__':
    Tree_GUIApp().run()
