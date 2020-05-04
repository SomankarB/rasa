from typing import Any, Optional, Tuple, Text, Dict, Set, List

from rasa.nlu.constants import (
    ENTITIES,
    INTENT,
    RESPONSE,
    RESPONSE_KEY_ATTRIBUTE,
    TEXT,
    RESPONSE_IDENTIFIER_DELIMITER,
)
from rasa.nlu.utils import ordered


class Message:
    def __init__(
        self,
        text: Text,
        data: Optional[Dict[Text, Any]] = None,
        output_properties: Optional[Set] = None,
        time: Optional[Text] = None,
        features: Optional[List["Features"]] = None,
    ) -> None:
        self.text = text
        self.time = time
        self.data = data if data else {}
        self.features = features if features else []

        if output_properties:
            self.output_properties = output_properties
        else:
            self.output_properties = set()

    def add_features(self, features: "Features") -> None:
        self.features.append(features)

    def set(self, prop, info, add_to_output=False) -> None:
        self.data[prop] = info
        if add_to_output:
            self.output_properties.add(prop)

    def get(self, prop, default=None) -> Any:
        if prop == TEXT:
            return self.text
        return self.data.get(prop, default)

    def as_dict_nlu(self) -> dict:
        """Get dict representation of message as it would appear in training data"""

        d = self.as_dict()
        if d.get(INTENT, None):
            d[INTENT] = self.get_combined_intent_response_key()
        d.pop(RESPONSE_KEY_ATTRIBUTE, None)
        d.pop(RESPONSE, None)
        return d

    def as_dict(self, only_output_properties=False) -> dict:
        if only_output_properties:
            d = {
                key: value
                for key, value in self.data.items()
                if key in self.output_properties
            }
        else:
            d = self.data

        # Filter all keys with None value. These could have come while building the Message object in markdown format
        d = {key: value for key, value in d.items() if value is not None}

        return dict(d, text=self.text)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Message):
            return False
        else:
            return (other.text, ordered(other.data)) == (self.text, ordered(self.data))

    def __hash__(self) -> int:
        return hash((self.text, str(ordered(self.data))))

    @classmethod
    def build(cls, text, intent=None, entities=None) -> "Message":
        data = {}
        if intent:
            split_intent, response_key = cls.separate_intent_response_key(intent)
            data[INTENT] = split_intent
            if response_key:
                data[RESPONSE_KEY_ATTRIBUTE] = response_key
        if entities:
            data[ENTITIES] = entities
        return cls(text, data)

    def get_combined_intent_response_key(self) -> Text:
        """Get intent as it appears in training data"""

        intent = self.get(INTENT)
        response_key = self.get(RESPONSE_KEY_ATTRIBUTE)
        response_key_suffix = (
            f"{RESPONSE_IDENTIFIER_DELIMITER}{response_key}" if response_key else ""
        )
        return f"{intent}{response_key_suffix}"

    @staticmethod
    def separate_intent_response_key(original_intent) -> Optional[Tuple[Any, Any]]:

        split_title = original_intent.split(RESPONSE_IDENTIFIER_DELIMITER)
        if len(split_title) == 2:
            return split_title[0], split_title[1]
        elif len(split_title) == 1:
            return split_title[0], None

    def get_sparse_features(self, attribute: Text):
        from nlu.featurizers.featurizer import Features
        import scipy.sparse

        # TODO: check what features to use

        features = [
            f
            for f in self.features
            if f.message_attribute == attribute and f.is_sparse()
        ]

        if not features:
            return None

        sequence_features = [f for f in features if f.type == Features.SEQUENCE]
        sentence_features = [f for f in features if f.type == Features.SENTENCE]

        combined_sequence_features = None
        for f in sequence_features:
            combined_sequence_features = Features.combine_features(
                combined_sequence_features, f
            )

        combined_sentence_features = None
        for f in sentence_features:
            combined_sentence_features = Features.combine_features(
                combined_sentence_features, f
            )

        return scipy.sparse.vstack(
            [combined_sequence_features, combined_sentence_features]
        )

    def get_dense_features(self, attribute: Text):
        from nlu.featurizers.featurizer import Features
        import numpy as np

        # TODO: check what features to use

        features = [
            f
            for f in self.features
            if f.message_attribute == attribute and f.is_dense()
        ]

        if not features:
            return None

        sequence_features = [f for f in features if f.type == Features.SEQUENCE]
        sentence_features = [f for f in features if f.type == Features.SENTENCE]

        combined_sequence_features = None
        for f in sequence_features:
            combined_sequence_features = Features.combine_features(
                combined_sequence_features, f
            )

        combined_sentence_features = None
        for f in sentence_features:
            combined_sentence_features = Features.combine_features(
                combined_sentence_features, f
            )

        # TODO
        #  stack sequence and sentence
        #  make sure they have the same dimension

        return np.concatenate([combined_sequence_features, combined_sentence_features])
