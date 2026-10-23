<?php
$pageTitle = 'Live Truck Monitoring | Smart Port';
$activeNav = 'tracking';

$stats = [
    ['label' => 'Tracked Trucks', 'value' => '24', 'note' => 'All GPS services online', 'class' => 'green'],
    ['label' => 'In Transit', 'value' => '14', 'note' => 'Active transportation tasks', 'class' => ''],
    ['label' => 'Available', 'value' => '6', 'note' => 'Ready for assignment', 'class' => 'green'],
    ['label' => 'Delayed', 'value' => '4', 'note' => 'Requires monitoring', 'class' => 'orange'],
];

$truckList = [
    [
        'id' => 'TRK-80579',
        'status' => 'In Transit',
        'statusClass' => 'active',
        'lines' => ['Task: TSK-1042', 'Destination: Yard B-12', 'ETA: 5 min']
    ],
    [
        'id' => 'TRK-80586',
        'status' => 'Available',
        'statusClass' => 'completed',
        'lines' => ['Current Area: Berth 03', 'Current Task: None', 'Ready for assignment']
    ],
    [
        'id' => 'TRK-80584',
        'status' => 'In Transit',
        'statusClass' => 'active',
        'lines' => ['Task: TSK-1043', 'Destination: Berth 05', 'ETA: 8 min']
    ],
    [
        'id' => 'TRK-80591',
        'status' => 'Delayed',
        'statusClass' => 'pending',
        'lines' => ['Task: TSK-1039', 'Current Area: Road B2', 'Congestion detected']
    ]
];

include 'header.php';
?>

<main>
<div class="page-container">

    <h1 class="page-title">Live Truck Monitoring</h1>
    <p class="page-description">
        View current truck locations, assignments and operational status across
        the terminal.
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

    <div class="tracking-layout">

        <div class="panel">
            <h2 class="panel-title">Terminal Live Map</h2>

            <div class="map-area">

                <div class="road horizontal"></div>
                <div class="road vertical"></div>

                <div class="location-label" style="left:20px; top:30px;">
                    Berth Area
                </div>

                <div class="location-label" style="right:20px; top:30px;">
                    Yard A
                </div>

                <div class="location-label" style="right:20px; bottom:30px;">
                    Yard B
                </div>

                <div class="location-label" style="left:20px; bottom:30px;">
                    Transfer Zone
                </div>

                <div class="truck-marker" style="left:25%; top:42%;" title="TRK-80579">
                    🚚
                </div>

                <div class="truck-marker available" style="left:51%; top:20%;" title="TRK-80586">
                    🚚
                </div>

                <div class="truck-marker" style="left:68%; top:46%;" title="TRK-80584">
                    🚚
                </div>

                <div class="truck-marker warning" style="left:45%; top:70%;" title="TRK-80591">
                    🚚
                </div>

                <div class="map-legend">
                    <span class="green">● Available</span>
                    &nbsp;&nbsp;
                    <span style="color:#174b70;">● In Transit</span>
                    &nbsp;&nbsp;
                    <span class="orange">● Delayed</span>
                </div>

            </div>
        </div>

        <div class="panel">
            <h2 class="panel-title">Truck Status</h2>

            <?php foreach ($truckList as $item): ?>
                <div class="truck-list-item">
                    <div class="truck-list-top">
                        <span class="truck-id"><?php echo htmlspecialchars($item['id']); ?></span>
                        <span class="status <?php echo htmlspecialchars($item['statusClass']); ?>">
                            <?php echo htmlspecialchars($item['status']); ?>
                        </span>
                    </div>
                    <div class="truck-info">
                        <?php foreach ($item['lines'] as $line): ?>
                            <?php echo htmlspecialchars($line); ?><br>
                        <?php endforeach; ?>
                    </div>
                </div>
            <?php endforeach; ?>

        </div>

    </div>
</div>
</main>

<?php include 'footer.php'; ?>
