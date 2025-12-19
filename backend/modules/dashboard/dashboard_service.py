from datetime import datetime, timedelta

from backend.models import SensorData
from backend.state import AppState


def get_sensor_data(state: AppState, days: int = 3) -> list[SensorData]:
	n_days_ago = datetime.now() - timedelta(days=days)

	with state.get_db() as db:
		sensor_data = (
			db.query(SensorData)
			.filter(SensorData.timestamp >= n_days_ago)
			.order_by(SensorData.timestamp.asc())
			.all()
		)

		return sensor_data
