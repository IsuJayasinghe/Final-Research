<?php
$pageTitle = 'Task Assignment | Smart Port';
$activeNav = 'solutions';

$pickups = ['Berth 01', 'Berth 02', 'Berth 03', 'Berth 04', 'Yard A', 'Yard B'];
$destinations = ['Yard A-08', 'Yard B-12', 'Yard C-04', 'Yard D-02', 'Berth 01'];
$priorities = ['Low', 'Normal', 'High', 'Urgent'];
$trucks = [
    'TRK-80586 — Available — 0.8 km away',
    'TRK-80591 — Available — 1.2 km away',
    'TRK-80594 — Available — 1.7 km away'
];

include 'header.php';
?>

<main>
    <div class="page-container">

        <h1 class="page-title">Task Assignment & Routing</h1>
        <p class="page-description">
            Assign transportation tasks and generate route recommendations
            according to current truck and operational conditions.
        </p>

        <div class="form-card">

            <div class="form-grid">

                <div class="form-group">
                    <label for="taskId">Task ID</label>
                    <input id="taskId" type="text" value="TSK-1045">
                </div>

                <div class="form-group">
                    <label for="containerId">Container ID</label>
                    <input id="containerId" type="text" value="MSKU-982143-0" placeholder="Enter container ID">
                </div>

                <div class="form-group">
                    <label for="pickup">Pickup Location</label>
                    <select id="pickup">
                        <?php foreach ($pickups as $loc): ?>
                            <option <?php echo ($loc === 'Berth 03') ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($loc); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="form-group">
                    <label for="destination">Destination</label>
                    <select id="destination">
                        <?php foreach ($destinations as $dest): ?>
                            <option <?php echo ($dest === 'Yard B-12') ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($dest); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="form-group">
                    <label for="priority">Task Priority</label>
                    <select id="priority">
                        <?php foreach ($priorities as $prio): ?>
                            <option <?php echo ($prio === 'Normal') ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($prio); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

                <div class="form-group">
                    <label for="truck">Recommended Truck</label>
                    <select id="truck">
                        <?php foreach ($trucks as $idx => $trk): ?>
                            <option <?php echo ($idx === 0) ? 'selected' : ''; ?>>
                                <?php echo htmlspecialchars($trk); ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </div>

            </div>

            <div class="route-preview">
                <h4>Recommended Route</h4>

                <div class="route-details">
                    <div>
                        <strong>Route</strong>
                        Berth 03 → Road B2 → Yard B-12
                    </div>

                    <div>
                        <strong>Distance</strong>
                        2.4 km
                    </div>

                    <div>
                        <strong>Estimated Time</strong>
                        7 min
                    </div>

                    <div>
                        <strong>Congestion</strong>
                        <span class="green">Low</span>
                    </div>
                </div>
            </div>

            <button class="btn" type="button" onclick="assignTask()">
                Assign Task
            </button>

        </div>

    </div>
</main>

<?php include 'footer.php'; ?>

<script>
function assignTask() {
    const taskId = document.getElementById("taskId").value;
    const truck = document.getElementById("truck").value;

    alert(
        "Task " + taskId +
        " has been assigned successfully.\n\nTruck: " + truck
    );
}
</script>
