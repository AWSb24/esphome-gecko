import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import select
from esphome.const import CONF_ID, CONF_TYPE
from . import gecko_spa_ns, GeckoSpa

DEPENDENCIES = ["gecko_spa"]

GeckoSpaSelect = gecko_spa_ns.class_("GeckoSpaSelect", select.Select, cg.Component)
GeckoSpaLockSelect = gecko_spa_ns.class_("GeckoSpaLockSelect", select.Select, cg.Component)

CONF_GECKO_SPA_ID = "gecko_spa_id"

TYPE_PROGRAM = "program"
TYPE_LOCK = "lock"

PROGRAM_OPTIONS = ["Away", "Standard", "Energy", "Super Energy", "Weekend"]
LOCK_OPTIONS = ["UNLOCK", "PARTIAL", "FULL"]

CONFIG_SCHEMA = cv.typed_schema(
    {
        TYPE_PROGRAM: select.select_schema(GeckoSpaSelect)
        .extend({cv.GenerateID(CONF_GECKO_SPA_ID): cv.use_id(GeckoSpa)})
        .extend(cv.COMPONENT_SCHEMA),
        TYPE_LOCK: select.select_schema(GeckoSpaLockSelect, icon="mdi:lock")
        .extend({cv.GenerateID(CONF_GECKO_SPA_ID): cv.use_id(GeckoSpa)})
        .extend(cv.COMPONENT_SCHEMA),
    },
    key=CONF_TYPE,
    default_type=TYPE_PROGRAM,
)


async def to_code(config):
    parent = await cg.get_variable(config[CONF_GECKO_SPA_ID])
    if config[CONF_TYPE] == TYPE_LOCK:
        var = await select.new_select(config, options=LOCK_OPTIONS)
        await cg.register_component(var, config)
        cg.add(var.set_parent(parent))
        cg.add(parent.set_lock_select(var))
        return
    var = await select.new_select(config, options=PROGRAM_OPTIONS)
    await cg.register_component(var, config)
    cg.add(var.set_parent(parent))
    cg.add(parent.set_program_select(var))
