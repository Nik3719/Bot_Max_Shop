from maxapi.context.state_machine import State, StatesGroup

class RegState(StatesGroup):
    WAIT_NAME = State()
    WAIT_PHONE = State()

class OrderState(StatesGroup):
    WAIT_COMMENT = State()
    WAIT_CONFIRM = State()
