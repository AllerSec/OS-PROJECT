from .race_condition import run as run_race_condition
from .mutex_vs_spinlock import run as run_mutex_vs_spinlock
from .producer_consumer import run as run_producer_consumer
from .readers_writers import run as run_readers_writers
from .deadlock import run as run_deadlock
from .priority_inversion import run as run_priority_inversion

REGISTRY = {
    "race_condition": run_race_condition,
    "mutex_vs_spinlock": run_mutex_vs_spinlock,
    "producer_consumer": run_producer_consumer,
    "readers_writers": run_readers_writers,
    "deadlock": run_deadlock,
    "priority_inversion": run_priority_inversion,
}
