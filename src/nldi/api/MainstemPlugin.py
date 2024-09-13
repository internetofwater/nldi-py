from nldi.schemas.nldi_data import MainstemLookupModel
from . import APIPlugin
from .. import LOGGER
from typing import Any, Dict


class MainstemPlugin(APIPlugin):
    def __init__(self, name, **kwargs):
        super().__init__(name, **kwargs)
        self.id_field = MainstemLookupModel.nhdpv2_comid
        self.table_model = MainstemLookupModel

    def get(self, identifier: str):
        LOGGER.debug(f"{self.__class__.__name__} GET mainstem for: {identifier}")
        with self.session() as session:
            # Retrieve data from database as feature
            item = session.query(self.table_model).where(self.id_field == identifier).first()
            if not item:
                raise KeyError("No Mainstem found {self.id_field}={identifier}")
            mainstem = self._sqlalchemy_to_feature(item)
        return mainstem

    def _sqlalchemy_to_feature(self, item: MainstemLookupModel) -> Dict[str, Any]:
        # Add properties from item
        item_dict = item.__dict__
        item_dict.pop("_sa_instance_state")  # Internal SQLAlchemy metadata
        return item_dict
