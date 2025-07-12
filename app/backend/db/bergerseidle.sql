-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: localhost:3306
-- Tiempo de generación: 30-06-2025 a las 11:29:13
-- Versión del servidor: 8.0.30
-- Versión de PHP: 8.2.4

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `bergerseidle`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventories`
--

CREATE TABLE `inventories` (
  `id` int NOT NULL,
  `product_id` int NOT NULL,
  `location_id` int NOT NULL,
  `stock` int NOT NULL DEFAULT '0',
  `avergae_cost` int NOT NULL,
  `minimum_stock` int DEFAULT '0',
  `maximum_stock` int DEFAULT NULL,
  `last_update` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `added_date` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventories_audits`
--

CREATE TABLE `inventories_audits` (
  `id` int NOT NULL,
  `inventory_id` int NOT NULL,
  `previous_stock` int NOT NULL,
  `new_stock` int NOT NULL,
  `reason` varchar(255) DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `added_date` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventories_lots`
--

CREATE TABLE `inventories_lots` (
  `id` int NOT NULL,
  `inventory_id` int NOT NULL,
  `lot_item_id` int NOT NULL,
  `quantity` int NOT NULL,
  `added_date` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `inventories_movements`
--

CREATE TABLE `inventories_movements` (
  `id` int NOT NULL,
  `inventory_id` int NOT NULL,
  `lot_item_id` int NOT NULL,
  `movement_type_id` int NOT NULL,
  `quantity` int NOT NULL,
  `unit_cost` int NOT NULL,
  `reason` varchar(255) DEFAULT NULL,
  `reference_type` varchar(100) DEFAULT NULL,
  `added_date` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `locations`
--

CREATE TABLE `locations` (
  `id` int NOT NULL,
  `location` varchar(255) NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `locations`
--

INSERT INTO `locations` (`id`, `location`, `added_date`, `updated_date`) VALUES
(3, 'Bodega 1', '2025-06-28 19:43:06', NULL);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `lots`
--

CREATE TABLE `lots` (
  `id` int NOT NULL,
  `supplier_id` int DEFAULT NULL,
  `lot_number` varchar(100) NOT NULL,
  `arrival_date` date NOT NULL,
  `added_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `lot_items`
--

CREATE TABLE `lot_items` (
  `id` int NOT NULL,
  `lot_id` int NOT NULL,
  `product_id` int NOT NULL,
  `quantity` int NOT NULL,
  `unit_cost` decimal(10,2) NOT NULL,
  `expiration_date` date DEFAULT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `movement_types`
--

CREATE TABLE `movement_types` (
  `id` int NOT NULL,
  `movement_type` varchar(255) NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `orders`
--

CREATE TABLE `orders` (
  `id` int NOT NULL,
  `period` varchar(255) NOT NULL,
  `ship_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `bill_support` text NOT NULL,
  `bill_amount` int NOT NULL,
  `bank_wire_support` text NOT NULL,
  `bank_wire_amount` int NOT NULL,
  `profrom_support` text NOT NULL,
  `proform_amount` int NOT NULL,
  `dim_support` text NOT NULL,
  `dim_amount` int NOT NULL,
  `arrival_date` date NOT NULL,
  `delivery_date` date NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `orders_products`
--

CREATE TABLE `orders_products` (
  `id` int NOT NULL,
  `order_id` int NOT NULL,
  `product_id` int NOT NULL,
  `quantity` int NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `products`
--

CREATE TABLE `products` (
  `id` int NOT NULL,
  `code` varchar(255) NOT NULL,
  `product` varchar(255) NOT NULL,
  `description` text NOT NULL,
  `unit_measure` varchar(255) NOT NULL,
  `photo` text NOT NULL,
  `catalog` text NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `products`
--

INSERT INTO `products` (`id`, `code`, `product`, `description`, `unit_measure`, `photo`, `catalog`, `added_date`, `updated_date`) VALUES
(3, 'AB123', 'Aqua', '<p>AquaChoice SPORT B Green is a waterbased 2-component finish for highly stressed sports floors. It represents the latest innovation in two-component waterborne coatings as its hardener is completely free of isocyanate. This special chemistry offers excellent chemical and abrasion resistance. Its suitability for sports floors is proven by a test certificate in accordance with FIBA and MFMA. Due to its resistance, AquaChoice® Sport B Green can also be used on other heavily used parquet floors that have special slip resistance requirements.</p>', 'L', 'photo_2025_06_29_20_07_35_f9830ba4.jpg', 'catalog_2025_06_29_20_07_35_2bf42d3f.pdf', '2025-06-30 00:07:35', '2025-06-30 00:07:35');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `rols`
--

CREATE TABLE `rols` (
  `id` int NOT NULL,
  `rol` varchar(150) NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `rols`
--

INSERT INTO `rols` (`id`, `rol`, `added_date`, `updated_date`) VALUES
(1, 'Super Administrator', '2025-05-28 00:09:15', '2025-05-28 00:09:15'),
(2, 'Administrator', '2025-05-28 00:09:15', '2025-05-28 00:09:15'),
(3, 'Assistant', '2025-05-28 00:09:15', '2025-05-28 00:09:15'),
(4, 'Worker', '2025-05-28 00:09:15', '2025-05-28 00:09:15'),
(5, 'Customer', '2025-05-28 00:09:15', '2025-05-28 00:09:15');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `statuses`
--

CREATE TABLE `statuses` (
  `id` int NOT NULL,
  `status` varchar(255) NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `statuses`
--

INSERT INTO `statuses` (`id`, `status`, `added_date`, `updated_date`) VALUES
(1, 'In Request', '2025-06-28 16:04:50', '2025-06-28 16:04:50'),
(2, 'In Travel\r\n', '2025-06-28 16:04:50', '2025-06-28 16:04:50'),
(3, 'Arrived', '2025-06-28 16:07:13', '2025-06-28 16:07:13'),
(4, 'To Be Delivered', '2025-06-28 16:07:20', '2025-06-28 16:07:20');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `suppliers`
--

CREATE TABLE `suppliers` (
  `id` int NOT NULL,
  `supplier` varchar(255) NOT NULL,
  `added_date` int NOT NULL,
  `updated_date` int NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `rol_id` int NOT NULL,
  `rut` varchar(150) NOT NULL,
  `full_name` varchar(150) NOT NULL,
  `email` varchar(150) NOT NULL,
  `hashed_password` text NOT NULL,
  `phone` varchar(150) NOT NULL,
  `added_date` datetime NOT NULL,
  `updated_date` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `users`
--

INSERT INTO `users` (`id`, `rol_id`, `rut`, `full_name`, `email`, `hashed_password`, `phone`, `added_date`, `updated_date`) VALUES
(1, 1, '11111111-1', 'Super Administrator', 'superadmin@vitrificadoschile.com', '$2y$10$7SUnqa1YJJeKDR.KrEIvOehE5VbCXetG8rDaw9ftZO7aKO2r/PtqC', '111111', '2025-05-28 00:11:13', '2025-05-28 00:11:13'),
(2, 2, '22222222-2', 'Administrator', 'admin@vitrificadoschile.com', '$2y$10$7SUnqa1YJJeKDR.KrEIvOehE5VbCXetG8rDaw9ftZO7aKO2r/PtqC', '', '2025-06-01 16:22:48', '2025-06-01 16:22:48'),
(3, 3, '33333333-3', 'Assitant', 'assistant@vitrificadoschile.com', '$2y$10$F5lIuap9Wi.BsZTEaj4.eu0Ee0oXaXJe2DE3CtxqJOOcK06w8/BGu', '', '2025-06-01 16:24:50', '2025-06-01 16:24:50'),
(4, 4, '', 'Worker', 'worker@vitrificadoschile.com', '$2y$10$F5lIuap9Wi.BsZTEaj4.eu0Ee0oXaXJe2DE3CtxqJOOcK06w8/BGu', '', '2025-06-01 16:25:50', '2025-06-01 16:25:50');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `inventories`
--
ALTER TABLE `inventories`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `inventories_audits`
--
ALTER TABLE `inventories_audits`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `inventories_lots`
--
ALTER TABLE `inventories_lots`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `inventories_movements`
--
ALTER TABLE `inventories_movements`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `locations`
--
ALTER TABLE `locations`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `lots`
--
ALTER TABLE `lots`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `lot_items`
--
ALTER TABLE `lot_items`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `movement_types`
--
ALTER TABLE `movement_types`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `orders`
--
ALTER TABLE `orders`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `orders_products`
--
ALTER TABLE `orders_products`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `products`
--
ALTER TABLE `products`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `rols`
--
ALTER TABLE `rols`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `statuses`
--
ALTER TABLE `statuses`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `suppliers`
--
ALTER TABLE `suppliers`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD KEY `rol_id` (`rol_id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `inventories`
--
ALTER TABLE `inventories`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `inventories_audits`
--
ALTER TABLE `inventories_audits`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `inventories_lots`
--
ALTER TABLE `inventories_lots`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `inventories_movements`
--
ALTER TABLE `inventories_movements`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `locations`
--
ALTER TABLE `locations`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `lots`
--
ALTER TABLE `lots`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `lot_items`
--
ALTER TABLE `lot_items`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `movement_types`
--
ALTER TABLE `movement_types`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `orders`
--
ALTER TABLE `orders`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `orders_products`
--
ALTER TABLE `orders_products`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `products`
--
ALTER TABLE `products`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT de la tabla `rols`
--
ALTER TABLE `rols`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- AUTO_INCREMENT de la tabla `statuses`
--
ALTER TABLE `statuses`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT de la tabla `suppliers`
--
ALTER TABLE `suppliers`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
