<?php
$pageTitle = 'Features & Modules | Smart Port';
$activeNav = 'features';

$stats = [
    ['label' => 'Dispatch Latency', 'value' => '0.4s', 'note' => 'Real-time AI path computing', 'class' => 'green'],
    ['label' => 'Turnaround Velocity', 'value' => '+28%', 'note' => 'Container handling speedup', 'class' => 'green'],
    ['label' => 'Fuel & Energy Saved', 'value' => '-18%', 'note' => 'Idle travel reduction', 'class' => 'green'],
    ['label' => 'Tracking Accuracy', 'value' => '99.7%', 'note' => 'RFID & DGPS precision', 'class' => 'green'],
];

$modules = [
    [
        'name' => 'Dynamic Route Planner',
        'subsystem' => 'Internal Haulage',
        'tech' => 'A* & Reinforcement Learning',
        'impact' => 'Avoids corridor bottlenecks',
        'status' => 'Active',
        'statusClass' => 'active'
    ],
    [
        'name' => 'Quay Crane Scheduler',
        'subsystem' => 'Berths 01–06',
        'tech' => 'Mixed-Integer Linear Math',
        'impact' => 'Synchronizes tandem lifts',
        'status' => 'Active',
        'statusClass' => 'active'
    ],
    [
        'name' => 'Yard Stacking Optimizer',
        'subsystem' => 'Yard Blocks A–D',
        'tech' => 'Heuristic Reshuffle Engine',
        'impact' => 'Minimizes container re-handling',
        'status' => 'Active',
        'statusClass' => 'active'
    ],
    [
        'name' => 'Automated Gate OCR',
        'subsystem' => 'In/Out Gates 1–4',
        'tech' => 'High-Speed Computer Vision',
        'impact' => '12-sec turnaround per gate',
        'status' => 'Active',
        'statusClass' => 'active'
    ],
    [
        'name' => 'Fleet Health Predictor',
        'subsystem' => 'Haulers & AGVs',
        'tech' => 'IoT Telemetry Anomaly Detection',
        'impact' => 'Prevents route breakdowns',
        'status' => 'Active',
        'statusClass' => 'active'
    ]
];

$alerts = [
    ['title' => 'Route Engine Online', 'class' => 'green', 'text' => 'Dynamic hauler dispatch engine functioning at 100% capacity.'],
    ['title' => 'Yard Optimization Notice', 'class' => 'orange', 'text' => 'Block C-04 reshuffle scheduled for off-peak shift (22:00).'],
    ['title' => 'Crane Sync Active', 'class' => 'green', 'text' => 'Berth 03 twin-lift cranes synchronized with haulers TRK-80579 and TRK-80584.'],
    ['title' => 'Firmware Telemetry', 'class' => '', 'text' => 'GPS RTK base station signal strength at maximum (100%).'],
];

include 'header.php';
?>

<main>
    <div class="page-container">

        <h1 class="page-title">AI System Features & Capabilities</h1>
        <p class="page-description">
            Explore the intelligent automation modules powering terminal hauler routing,
            container stacking optimization, and quay crane synchronization.
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
                <h2 class="panel-title">Active AI Optimization Modules</h2>

                <table>
                    <thead>
                    <tr>
                        <th>Module Name</th>
                        <th>Subsystem</th>
                        <th>Methodology</th>
                        <th>Operational Impact</th>
                        <th>Status</th>
                    </tr>
                    </thead>

                    <tbody>
                    <?php foreach ($modules as $mod): ?>
                        <tr>
                            <td><strong><?php echo htmlspecialchars($mod['name']); ?></strong></td>
                            <td><?php echo htmlspecialchars($mod['subsystem']); ?></td>
                            <td><?php echo htmlspecialchars($mod['tech']); ?></td>
                            <td><?php echo htmlspecialchars($mod['impact']); ?></td>
                            <td>
                                <span class="status <?php echo htmlspecialchars($mod['statusClass']); ?>">
                                    <?php echo htmlspecialchars($mod['status']); ?>
                                </span>
                            </td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div class="panel">
                <h2 class="panel-title">System Status & Health</h2>

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
