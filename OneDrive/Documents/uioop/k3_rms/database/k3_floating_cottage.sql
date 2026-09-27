

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `k3_floating_cottage`
--

-- --------------------------------------------------------

--
-- Table structure for table `cottages`
--

CREATE TABLE `cottages` (
  `id` int(11) NOT NULL,
  `asset_code` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `capacity` int(11) NOT NULL,
  `base_rate` decimal(10,2) NOT NULL,
  `status` enum('Available','Reserved','In Use') NOT NULL DEFAULT 'Available',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `cottages`
--

INSERT INTO `cottages` (`id`, `asset_code`, `name`, `capacity`, `base_rate`, `status`, `created_at`) VALUES
(1, 'FC-01', 'Azure Breeze', 20, 2800.00, 'Available', '2026-04-04 04:31:44'),
(2, 'FC-02', 'Sea Haven', 20, 3400.00, 'Available', '2026-04-04 04:31:44'),
(3, 'FC-03', 'Driftwood Lounge', 20, 4200.00, 'Available', '2026-04-04 04:31:44');

-- --------------------------------------------------------

--
-- Table structure for table `customers`
--

CREATE TABLE `customers` (
  `id` int(11) NOT NULL,
  `full_name` varchar(120) NOT NULL,
  `contact_number` varchar(30) DEFAULT NULL,
  `email` varchar(120) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `customers`
--

INSERT INTO `customers` (`id`, `full_name`, `contact_number`, `email`, `created_at`, `updated_at`) VALUES
(2, 'Nirro', '09382877495', 'n@gmail.com', '2026-04-04 05:29:52', '2026-04-04 05:29:52');

-- --------------------------------------------------------

--
-- Table structure for table `motorboats`
--

CREATE TABLE `motorboats` (
  `id` int(11) NOT NULL,
  `asset_code` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `capacity` int(11) NOT NULL,
  `base_rate` decimal(10,2) NOT NULL,
  `status` enum('Available','Reserved','In Use') NOT NULL DEFAULT 'Available',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `motorboats`
--

INSERT INTO `motorboats` (`id`, `asset_code`, `name`, `capacity`, `base_rate`, `status`, `created_at`) VALUES
(1, 'MB-01', 'Wave Runner I', 20, 1700.00, 'Available', '2026-04-04 04:31:44'),
(2, 'MB-02', 'Wave Runner II', 20, 2200.00, 'Available', '2026-04-04 04:31:44'),
(3, 'MB-03', 'Wave Runner III', 20, 2800.00, 'Available', '2026-04-04 04:31:44');

-- --------------------------------------------------------

--
-- Table structure for table `reservations`
--

CREATE TABLE `reservations` (
  `id` int(11) NOT NULL,
  `reservation_code` varchar(30) NOT NULL,
  `customer_id` int(11) NOT NULL,
  `cottage_id` int(11) NOT NULL,
  `motorboat_id` int(11) NOT NULL,
  `destination` varchar(100) NOT NULL,
  `party_size` int(11) NOT NULL,
  `departure_time` datetime NOT NULL,
  `return_time` datetime NOT NULL,
  `total_price` decimal(10,2) NOT NULL,
  `status` enum('Reserved','In Use','Completed','Cancelled') NOT NULL DEFAULT 'Reserved',
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `completed_at` datetime DEFAULT NULL,
  `cancelled_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `reservations`
--

INSERT INTO `reservations` (`id`, `reservation_code`, `customer_id`, `cottage_id`, `motorboat_id`, `destination`, `party_size`, `departure_time`, `return_time`, `total_price`, `status`, `notes`, `created_at`, `updated_at`, `completed_at`, `cancelled_at`) VALUES
(2, 'K3-20260404132952161238', 2, 1, 1, 'Little Boracay', 6, '2026-04-04 15:00:00', '2026-04-04 19:00:00', 18000.00, 'Cancelled', 'Cancelled from Operations page.', '2026-04-04 05:29:52', '2026-04-04 05:58:30', NULL, '2026-04-04 13:58:30'),
(3, 'K3-20260404143102916777', 2, 1, 1, 'Snorkeling Area', 6, '2026-04-05 06:00:00', '2026-04-05 14:00:00', 36000.00, 'In Use', '', '2026-04-04 06:31:02', '2026-04-04 06:31:16', NULL, NULL);

-- --------------------------------------------------------

--
-- Stand-in structure for view `vw_active_reservations`
-- (See below for the actual view)
--
CREATE TABLE `vw_active_reservations` (
`id` int(11)
,`reservation_code` varchar(30)
,`customer_id` int(11)
,`customer_name` varchar(480)
,`contact_number` varchar(30)
,`email` varchar(120)
,`cottage_id` int(11)
,`cottage_code` varchar(20)
,`cottage_name` varchar(100)
,`cottage_status` enum('Available','Reserved','In Use')
,`motorboat_id` int(11)
,`motorboat_code` varchar(20)
,`motorboat_name` varchar(100)
,`motorboat_status` enum('Available','Reserved','In Use')
,`destination` varchar(100)
,`party_size` int(11)
,`departure_time` datetime
,`return_time` datetime
,`status` enum('Reserved','In Use','Completed','Cancelled')
,`total_price` decimal(10,2)
,`remaining_session_minutes` bigint(21)
);

-- --------------------------------------------------------

--
-- Structure for view `vw_active_reservations`
--
DROP TABLE IF EXISTS `vw_active_reservations`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `vw_active_reservations`  AS SELECT `r`.`id` AS `id`, `r`.`reservation_code` AS `reservation_code`, `r`.`customer_id` AS `customer_id`, CASE WHEN trim(coalesce(`c`.`full_name`,'')) = '' THEN 'Guest' ELSE concat(ucase(left(trim(`c`.`full_name`),1)),lcase(substr(trim(`c`.`full_name`),2))) END AS `customer_name`, `c`.`contact_number` AS `contact_number`, `c`.`email` AS `email`, `r`.`cottage_id` AS `cottage_id`, `fc`.`asset_code` AS `cottage_code`, `fc`.`name` AS `cottage_name`, `fc`.`status` AS `cottage_status`, `r`.`motorboat_id` AS `motorboat_id`, `mb`.`asset_code` AS `motorboat_code`, `mb`.`name` AS `motorboat_name`, `mb`.`status` AS `motorboat_status`, `r`.`destination` AS `destination`, `r`.`party_size` AS `party_size`, `r`.`departure_time` AS `departure_time`, `r`.`return_time` AS `return_time`, `r`.`status` AS `status`, `r`.`total_price` AS `total_price`, greatest(timestampdiff(MINUTE,current_timestamp(),`r`.`return_time`),0) AS `remaining_session_minutes` FROM (((`reservations` `r` join `customers` `c` on(`c`.`id` = `r`.`customer_id`)) join `cottages` `fc` on(`fc`.`id` = `r`.`cottage_id`)) join `motorboats` `mb` on(`mb`.`id` = `r`.`motorboat_id`)) WHERE `r`.`status` in ('Reserved','In Use') ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `cottages`
--
ALTER TABLE `cottages`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `asset_code` (`asset_code`);

--
-- Indexes for table `customers`
--
ALTER TABLE `customers`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `contact_number` (`contact_number`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `motorboats`
--
ALTER TABLE `motorboats`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `asset_code` (`asset_code`);

--
-- Indexes for table `reservations`
--
ALTER TABLE `reservations`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `reservation_code` (`reservation_code`),
  ADD KEY `fk_reservations_customer` (`customer_id`),
  ADD KEY `fk_reservations_cottage` (`cottage_id`),
  ADD KEY `fk_reservations_motorboat` (`motorboat_id`),
  ADD KEY `idx_reservations_status_schedule` (`status`,`departure_time`,`return_time`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `cottages`
--
ALTER TABLE `cottages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=133;

--
-- AUTO_INCREMENT for table `customers`
--
ALTER TABLE `customers`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `motorboats`
--
ALTER TABLE `motorboats`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=133;

--
-- AUTO_INCREMENT for table `reservations`
--
ALTER TABLE `reservations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `reservations`
--
ALTER TABLE `reservations`
  ADD CONSTRAINT `fk_reservations_cottage` FOREIGN KEY (`cottage_id`) REFERENCES `cottages` (`id`),
  ADD CONSTRAINT `fk_reservations_customer` FOREIGN KEY (`customer_id`) REFERENCES `customers` (`id`),
  ADD CONSTRAINT `fk_reservations_motorboat` FOREIGN KEY (`motorboat_id`) REFERENCES `motorboats` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
