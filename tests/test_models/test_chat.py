import pytest
from bson.objectid import ObjectId
from unittest.mock import MagicMock
from models.chat import ChatModel
from datetime import datetime, timezone

class TestChatModel:
    @pytest.fixture
    def mock_collection(self):
        return MagicMock()
        
    @pytest.fixture
    def chat_model(self, mock_collection):
        return ChatModel(mock_collection)
    
def test_send_message(self, chat_model, mock_collection):
        # Setup
        sender = "user1"
        receiver = "user2"
        content = "Hello, how are you?"
        mock_collection.insert_one.return_value = MagicMock(inserted_id=ObjectId("60d21b4667d0d8992e610c89"))
        
        # Execute
        result = chat_model.send_message(sender, receiver, content)
        
        # Verify
        assert isinstance(result, str)
        assert len(result) == 24  # ObjectId as string has 24 chars
        mock_collection.insert_one.assert_called_once()
        
        # Check the argument passed to insert_one
        call_args = mock_collection.insert_one.call_args[0][0]
        assert call_args["sender"] == sender
        assert call_args["receiver"] == receiver
        assert call_args["content"] == content
        assert isinstance(call_args["timestamp"], datetime)
    
def test_get_conversation(self, chat_model, mock_collection):
    # Setup
    user1 = "user1"
    user2 = "user2"
    expected_messages = [
        {"_id": ObjectId(), "sender": user1, "receiver": user2, "content": "Hi"},
        {"_id": ObjectId(), "sender": user2, "receiver": user1, "content": "Hello"}
    ]
    mock_cursor = MagicMock()
    mock_collection.find.return_value = mock_cursor
    mock_cursor.sort.return_value = expected_messages
    
    # Execute
    results = chat_model.get_conversation(user1, user2)
    
    # Verify
    assert results == expected_messages
    mock_collection.find.assert_called_once_with({
        "$or": [
            {"sender": user1, "receiver": user2},
            {"sender": user2, "receiver": user1}
        ]
    })
    mock_cursor.sort.assert_called_once_with("timestamp", 1)

def test_get_recent_contacts(self, chat_model, mock_collection):
    # Setup
    username = "user1"
    expected_contacts = ["user2", "user3", "user4"]
    
    # Setup mock for the aggregation pipeline
    mock_aggregate_result = [
        {"_id": "user2", "latest_time": datetime.now(timezone.utc)},
        {"_id": "user3", "latest_time": datetime.now(timezone.utc)},
        {"_id": "user4", "latest_time": datetime.now(timezone.utc)}
    ]
    mock_collection.aggregate.return_value = mock_aggregate_result
    
    # Execute
    results = chat_model.get_recent_contacts(username)
    
    # Verify
    assert results == expected_contacts
    mock_collection.aggregate.assert_called_once()
    
    # Verify the pipeline structure
    pipeline = mock_collection.aggregate.call_args[0][0]
    
    # Check pipeline has the correct steps
    assert len(pipeline) >= 5
    assert "$match" in pipeline[0]
    assert "$project" in pipeline[1]
    assert "$sort" in pipeline[2]
    assert "$group" in pipeline[3]
    assert "$sort" in pipeline[4]
    
    # Verify the match condition
    match_condition = pipeline[0]["$match"]
    assert "$or" in match_condition
    assert len(match_condition["$or"]) == 2
    assert {"sender": username} in match_condition["$or"]
    assert {"receiver": username} in match_condition["$or"]
    
    # Verify projection
    projection = pipeline[1]["$project"]
    assert "other" in projection
    assert "timestamp" in projection
    
    # Verify sorting
    assert pipeline[2]["$sort"]["timestamp"] == -1
    
    # Verify grouping
    grouping = pipeline[3]["$group"]
    assert grouping["_id"] == "$other"
    assert "latest_time" in grouping
    assert grouping["latest_time"]["$first"] == "$timestamp"
    
    # Verify final sorting
    assert pipeline[4]["$sort"]["latest_time"] == -1