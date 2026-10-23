<?php
$pageTitle = 'Operations Dashboard | Smart Port';
$activeNav = 'home';

// Sample operational data for the dashboard
$stats = [
    ['label' => 'Active Trucks', 'value' => '24', 'note' => '18 currently assigned', 'class' => 'green'],
    ['label' => 'Available Trucks', 'value' => '6', 'note' => 'Ready for assignment', 'class' => ''],
    ['label' => 'Pending Tasks', 'value' => '8', 'note' => '2 high-priority tasks', 'class' => 'orange'],
    ['label' => 'Average Utilization', 'value' => '82%', 'note' => 'Current operational period', 'class' => 'green'],
];

$tasks = [
    ['id' => 'TSK-1042', 'truck' => 'TRK-80579', 'pickup' => 'Berth 03', 'dest' => 'Yard B-12', 'priority' => 'High', 'status' => 'In Progress', 'statusClass' => 'active'],
    ['id' => 'TSK-1043', 'truck' => 'TRK-80584', 'pickup' => 'Yard A-08', 'dest' => 'Berth 05', 'priority' => 'Normal', 'status' => 'In Progress', 'statusClass' => 'active'],
    ['id' => 'TSK-1044', 'truck' => '—', 'pickup' => 'Berth 02', 'dest' => 'Yard C-04', 'priority' => 'High', 'status' => 'Pending', 'statusClass' => 'pending'],
    ['id' => 'TSK-1041', 'truck' => 'TRK-80571', 'pickup' => 'Yard D-02', 'dest' => 'Berth 01', 'priority' => 'Normal', 'status' => 'Completed', 'statusClass' => 'completed'],
];

$alerts = [
    ['title' => 'High Congestion', 'class' => 'red', 'text' => 'Route B2 → Yard C currently experiencing increased delay.'],
    ['title' => 'Priority Task', 'class' => 'orange', 'text' => 'TSK-1044 requires truck assignment.'],
    ['title' => 'Truck Status Update', 'class' => '', 'text' => 'TRK-80571 completed its assigned transportation task.'],
    ['title' => 'System Update', 'class' => 'green', 'text' => 'Current truck locations successfully synchronized.'],
];

include 'header.php';
?>

<main>
    <div class="page-container">

        <h1 class="page-title">Operations Dashboard</h1>
        <p class="page-description">
            Monitor truck activity, transportation tasks and current
            operational conditions in real time.
        </p>

        <section class="stats-grid">
            <?php foreach ($stats as $stat): ?>
                <div class="stat-card">
                    <div class="stat-label"><?php echo htmlspecialchars($stat['label']); ?></div>
                    <div class="stat-value"><?php echo htmlspecialchars($stat['value']); ?></div>
                    <div class="stat-note <?php echo htmlspecialchars($stat['class']); ?>">
                        <?php echo htmlspecialchars($stat['note']); ?>
                    </div>
                </div>
            <?php endforeach; ?>
        </section>

        <section class="dashboard-grid">

            <div class="panel">
                <h2 class="panel-title">Current Transportation Tasks</h2>

                <table>
                    <thead>
                    <tr>
                        <th>Task ID</th>
                        <th>Truck</th>
                        <th>Pickup</th>
                        <th>Destination</th>
                        <th>Priority</th>
                        <th>Status</th>
                    </tr>
                    </thead>

                    <tbody>
                    <?php foreach ($tasks as $task): ?>
                        <tr>
                            <td><?php echo htmlspecialchars($task['id']); ?></td>
                            <td><?php echo htmlspecialchars($task['truck']); ?></td>
                            <td><?php echo htmlspecialchars($task['pickup']); ?></td>
                            <td><?php echo htmlspecialchars($task['dest']); ?></td>
                            <td><?php echo htmlspecialchars($task['priority']); ?></td>
                            <td>
                                <span class="status <?php echo htmlspecialchars($task['statusClass']); ?>">
                                    <?php echo htmlspecialchars($task['status']); ?>
                                </span>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div class="panel">
                <h2 class="panel-title">Operational Alerts</h2>

                <?php foreach ($alerts as $alert): ?>
                    <div class="alert-item">
                        <div class="alert-title <?php echo htmlspecialchars($alert['class']); ?>">
                            <?php echo htmlspecialchars($alert['title']); ?>
                        </div>
                        <div class="alert-text">
                            <?php echo htmlspecialchars($alert['text']); ?>
                        </div>
                    </div>
                <?php endforeach; ?>
            </div>

        </section>

    </div>
</main>

<?php include 'footer.php'; ?>
