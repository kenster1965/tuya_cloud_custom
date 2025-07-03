"""Tuya Cloud Custom - Robust Select platform with options support."""

import logging
from homeassistant.components.select import SelectEntity
from .const import DOMAIN
from .helpers.helper import build_entity_attrs, build_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Tuya Cloud Custom selects."""
    devices = hass.data[DOMAIN]["devices"]
    selects = []
    for device in devices:
        for dp in device.get("entities", []):
            if dp.get("platform") == "select" and dp.get("enabled", True):
                selects.append(TuyaCloudSelect(hass, device, dp))
    async_add_entities(selects)
    _LOGGER.info("[%s] ✅ Registered %s selects", DOMAIN, len(selects))


class TuyaCloudSelect(SelectEntity):
    """Tuya Cloud Custom Select with robust options support."""

    def __init__(self, hass, device, dp):
        self._hass = hass
        self._device = device
        self._dp = dp
        self._state = None

        attrs = build_entity_attrs(device, dp, "select")

        self._attr_has_entity_name = True
        self._attr_name = attrs["name"]
        self._attr_unique_id = attrs["unique_id"]
        self._attr_entity_category = attrs.get("entity_category")
        if "icon" in attrs:
            self._attr_icon = attrs["icon"]

        self._options_map = dp.get("options", {})
        self._is_passive = dp.get("is_passive_entity", False)

        if not self._options_map:
            _LOGGER.warning(
                "[%s] ⚠️ Select entity %s has no options defined!",
                DOMAIN, self._attr_unique_id
            )

        # Maps: key → label, label → key
        self._key_to_label = self._options_map
        self._label_to_key = {v: k for k, v in self._options_map.items()}

        self._attr_options = list(self._options_map.values())

        key = (device["tuya_device_id"], dp["code"])
        self._hass.data[DOMAIN]["entities"][key] = self

        _LOGGER.debug(
            "[%s] ✅ Registered select entity: %s | Options: %s | Passive=%s",
            DOMAIN, key, self._attr_options, self._is_passive
        )

    @property
    def current_option(self):
        return self._state

    @property
    def device_info(self):
        return build_device_info(self._device)

    async def async_update(self):
        """No polling — push only."""
        pass

    async def async_update_from_status(self, value):
        """Update from Status manager — convert raw key to label."""
        try:
            raw_key = str(value)
            label = self._key_to_label.get(raw_key, raw_key)
            self._state = label

            _LOGGER.debug(
                "[%s] ⚙️ Select %s: raw=%s | label=%s",
                DOMAIN,
                self._attr_unique_id,
                raw_key,
                label
            )

        except Exception as e:
            _LOGGER.exception("[%s] ❌ Failed to parse select value: %s", DOMAIN, e)
            self._state = None

        self.async_write_ha_state()

    async def async_select_option(self, option: str):
        """Handle user selecting a new option in the UI."""
        if self._is_passive:
            _LOGGER.info(
                "[%s] 🚫 Select %s is passive — command not sent (UI-only update)",
                DOMAIN, self._attr_unique_id
            )
            self._state = option
            self.async_write_ha_state()
            return

        if option not in self._label_to_key:
            _LOGGER.warning(
                "[%s] ❌ Invalid option selected: %s for %s",
                DOMAIN, option, self._attr_unique_id
            )
            return

        key_to_send = self._label_to_key[option]

        try:
            await self._hass.data[DOMAIN]["status"].async_send_command(
                self._device["tuya_device_id"],
                {self._dp["code"]: key_to_send}
            )

            _LOGGER.info(
                "[%s] ✅ Sent new option %s (key=%s) for %s",
                DOMAIN, option, key_to_send, self._attr_unique_id
            )

        except Exception as e:
            _LOGGER.exception("[%s] ❌ Failed to send select option: %s", DOMAIN, e)
