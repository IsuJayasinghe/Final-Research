<?php
$pageTitle = 'Task Management | Smart Port';
$activeNav = 'tasks';

$stats = [
    ['label' => 'Total Tasks Today', 'value' => '64', 'note' => 'Current operational period', 'class' => ''],
    ['label' => 'In Progress', 'value' => '18', 'note' => 'Currently being executed', 'class' => 'green'],
    ['label' => 'Pending', 'value' => '8', 'note' => 'Awaiting assignment', 'class' => 'orange'],
    ['label' => 'Completed', 'value' => '38', 'note' => 'Completed today', 'class' => 'green'],
];

$tasks = [
    [
        'id' => 'TSK-1042',
        'container' => 'MAEU3483419',
        'pickup' => 'Berth 03',
        'dest' => 'Yard B-12',
        'truck' => 'TRK-80579',
        'priority' => 'High',
        'prioClass' => 'priority-high',
        'status' => 'In Progress',
        'statusClass' => 'active',
        'dataStatus' => 'active',
        'actionText' => 'View',
        'actionUrl' => ''
    ],
    [
        'id' => 'TSK-1043',
        'container' => 'MSCU7281954',
        'pickup' => 'Yard A-08',
        'dest' => 'Berth 05',
        'truck' => 'TRK-80584',
        'priority' => 'Normal',
        'prioClass' => 'priority-normal',
        'status' => 'In Progress',
        'statusClass' => 'active',
        'dataStatus' => 'active',
        'actionText' => 'View',
        'actionUrl' => ''
    ],
    [
        'id' => 'TSK-1044',
        'container' => 'CMAU5812098',
        'pickup' => 'Berth 02',
        'dest' => 'Yard C-04',
        'truck' => 'Not Assigned',
        'priority' => 'High',
        'prioClass' => 'priority-high',
        'status' => 'Pending',
        'statusClass' => 'pending',
        'dataStatus' => 'pending',
        'actionText' => 'Assign',
        'actionUrl' => 'task-assignment.php'
    ],
    [
        'id' => 'TSK-1045',
        'container' => 'OOLU9341852',
        'pickup' => 'Yard B-07',
        'dest' => 'Berth 04',
        'truck' => 'Not Assigned',
        'priority' => 'Normal',
        'prioClass' => 'priority-normal',
        'status' => 'Pending',
        'statusClass' => 'pending',
        'dataStatus' => 'pending',
        'actionText' => 'Assign',
        'actionUrl' => 'task-assignment.php'
    ],
    [
        'id' => 'TSK-1041',
        'container' => 'HLXU6293817',
        'pickup' => 'Yard D-02',
        'dest' => 'Berth 01',
        'truck' => 'TRK-80571',
        'priority' => 'Normal',
        'prioClass' => 'priority-normal',
        'status' => 'Completed',
        'statusClass' => 'completed',
        'dataStatus' => 'completed',
        'actionText' => 'Details',
        'actionUrl' => ''
    ],
];

include 'header.php';
?>

<main>
<div class="page-container">

    <h1 class="page-title">Task Management</h1>

    <p class="page-description">
        Monitor transportation tasks, priorities, assigned trucks and
        completion status.
    </p>

    <div class="stats-grid">
        <?php foreach ($stats as $stat): ?>
            <div class="stat-card">
                <div class="stat-label"><?php echo htmlspecialchars($stat['label']); ?></div>
                <div class="stat-value"><?php echo htmlspecialchars($stat['value']); ?></div>
                <div class="stat-note <?php echo htmlspecialchars($stat['class']); ?>">
                    <?php echo htmlspecialchars($stat['note']); ?>
                </div>
            </div>
        <?php endforeach; ?>
    </div>

    <div class="panel">

        <div class="toolbar">

            <div class="filters">
                <button class="filter-btn active-filter" onclick="filterTasks('all', this)">
                    All Tasks
                </button>

                <button class="filter-btn" onclick="filterTasks('pending', this)">
                    Pending
                </button>

                <button class="filter-btn" onclick="filterTasks('active', this)">
                    In Progress
                </button>

                <button class="filter-btn" onclick="filterTasks('completed', this)">
                    Completed
                </button>
            </div>

            <a href="task-assignment.php">
                <button class="btn" style="margin-top:0;">
                    + New Task
                </button>
            </a>

        </div>

        <table id="taskTable">
            <thead>
            <tr>
                <th>Task ID</th>
                <th>Container</th>
                <th>Pickup</th>
                <th>Destination</th>
                <th>Truck</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Action</th>
            </tr>
            </thead>

            <tbody>
            <?php foreach ($tasks as $row): ?>
                <tr data-status="<?php echo htmlspecialchars($row['dataStatus']); ?>">
                    <td><?php echo htmlspecialchars($row['id']); ?></td>
                    <td><?php echo htmlspecialchars($row['container']); ?></td>
                    <td><?php echo htmlspecialchars($row['pickup']); ?></td>
                    <td><?php echo htmlspecialchars($row['dest']); ?></td>
                    <td><?php echo htmlspecialchars($row['truck']); ?></td>
                    <td class="<?php echo htmlspecialchars($row['prioClass']); ?>">
                        <?php echo htmlspecialchars($row['priority']); ?>
                    </td>
                    <td>
                        <span class="status <?php echo htmlspecialchars($row['statusClass']); ?>">
                            <?php echo htmlspecialchars($row['status']); ?>
                        </span>
                    </td>
                    <td>
                        <?php if (!empty($row['actionUrl'])): ?>
                            <button class="action-btn" onclick="location.href='<?php echo htmlspecialchars($row['actionUrl']); ?>'">
                                <?php echo htmlspecialchars($row['actionText']); ?>
                            </button>
                        <?php else: ?>
                            <button class="action-btn">
                                <?php echo htmlspecialchars($row['actionText']); ?>
                            </button>
                        <?php endif; ?>
                    </td>
                </tr>
            <?php endforeach; ?>
            </tbody>
        </table>

        <div class="summary-bar">
            Showing transportation tasks for the current operational period.
            Task information is updated when drivers report progress or
            operational conditions change.
        </div>

    </div>

</div>
</main>

<?php include 'footer.php'; ?>

<script>
function filterTasks(status, button) {
    const rows = document.querySelectorAll("#taskTable tbody tr");

    rows.forEach(row => {
        if (status === "all" || row.dataset.status === status) {
            row.style.display = "";
        } else {
            row.style.display = "none";
        }
    });

    document.querySelectorAll(".filter-btn").forEach(btn =>
        btn.classList.remove("active-filter")
    );

    button.classList.add("active-filter");
}
</script>
