CREATE TABLE `agent` (
  `id` smallint(5) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(64) NOT NULL DEFAULT '',
  `user_id` int(10) unsigned DEFAULT NULL,
  `staff_id` int(11) unsigned DEFAULT NULL,
  `type` enum('Staff Member','Organization','Automated') NOT NULL DEFAULT 'Staff Member',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `caged_donor` (
  `id` int(10) NOT NULL AUTO_INCREMENT,
  `gift_id` int(10) unsigned DEFAULT NULL,
  `gift_searchable_id` binary(16) DEFAULT NULL,
  `campaign_id` int(10) DEFAULT NULL,
  `customer_id` varchar(64) DEFAULT NULL,
  `user_email_address` varchar(255) NOT NULL,
  `user_first_name` varchar(64) DEFAULT '',
  `user_last_name` varchar(64) DEFAULT NULL,
  `user_address` varchar(255) DEFAULT NULL,
  `user_state` char(2) DEFAULT NULL,
  `user_city` varchar(64) DEFAULT NULL,
  `user_zipcode` varchar(5) DEFAULT NULL,
  `user_phone_number` bigint(10) unsigned DEFAULT '0',
  `times_viewed` smallint(5) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `campaign` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(80) DEFAULT NULL,
  `description` varchar(80) DEFAULT NULL,
  `date_from_utc` datetime DEFAULT NULL,
  `date_to_utc` datetime DEFAULT NULL,
  `message` text,
  `background` tinyint(1) DEFAULT '0',
  `photo_type` varchar(80) DEFAULT NULL,
  `video_name` varchar(80) DEFAULT NULL,
  `video_url` varchar(80) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT '1',
  `is_default` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `campaign_amounts` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `amount` decimal(10,2) NOT NULL,
  `weight` smallint(5) NOT NULL,
  `campaign_id` int(10) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `gift` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `searchable_id` binary(16) DEFAULT NULL,
  `user_id` int(10) DEFAULT NULL,
  `campaign_id` int(10) DEFAULT NULL,
  `customer_id` varchar(36) DEFAULT '',
  `method_used_id` tinyint(3) DEFAULT '1',
  `sourced_from_agent_id` smallint(5) unsigned DEFAULT NULL,
  `given_to` enum('ABI','ACTION','BECK','GREEN','INTER','MCRI','NERF','P-USA','PROD','UNRES','VIDEO','TBD','SUPPORT') NOT NULL DEFAULT 'ACTION',
  `recurring_subscription_id` varchar(32) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `gift_thank_you_letter` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `gift_id` int(10) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `method_used` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(128) NOT NULL,
  `billing_address_required` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `paypal_etl` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `enacted_by_agent_id` smallint(5) unsigned NOT NULL,
  `file_name` varchar(128) NOT NULL,
  `date_in_utc` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `queued_donor` (
  `id` int(10) NOT NULL AUTO_INCREMENT,
  `gift_id` int(10) unsigned DEFAULT NULL,
  `gift_searchable_id` binary(16) DEFAULT NULL,
  `campaign_id` int(10) DEFAULT NULL,
  `customer_id` varchar(64) DEFAULT NULL,
  `user_email_address` varchar(255) NOT NULL,
  `user_first_name` varchar(64) DEFAULT '',
  `user_last_name` varchar(64) DEFAULT NULL,
  `user_address` varchar(255) DEFAULT NULL,
  `user_state` char(2) DEFAULT NULL,
  `user_city` varchar(64) DEFAULT NULL,
  `user_zipcode` varchar(5) DEFAULT NULL,
  `user_phone_number` bigint(10) unsigned DEFAULT '0',
  `times_viewed` smallint(5) unsigned DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `transaction` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `gift_id` int(10) unsigned NOT NULL,
  `date_in_utc` datetime NOT NULL,
  `receipt_sent_in_utc` datetime DEFAULT NULL,
  `enacted_by_agent_id` smallint(5) unsigned DEFAULT NULL,
  `type` enum('Gift','Reallocation','Refund','Void','Deposit to Bank','Bounced','Dispute','Note','Fine') NOT NULL DEFAULT 'Gift',
  `status` enum('Accepted','Completed','Declined','Denied','Failed','Forced','Lost','Refused','Requested','Won','Thank You Sent') NOT NULL DEFAULT 'Accepted',
  `reference_number` varchar(32) DEFAULT '',
  `gross_gift_amount` decimal(10,2) NOT NULL,
  `fee` decimal(8,2) NOT NULL,
  `notes` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `unresolved_paypal_etl_transaction` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `enacted_by_agent_id` smallint(5) unsigned DEFAULT NULL,
  `date` varchar(20) DEFAULT NULL,
  `time` varchar(20) DEFAULT NULL,
  `time_zone` varchar(5) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `type` varchar(255) DEFAULT NULL,
  `status` varchar(64) DEFAULT NULL,
  `subject` varchar(255) DEFAULT NULL,
  `gross` varchar(64) DEFAULT NULL,
  `fee` varchar(64) DEFAULT NULL,
  `from_email_address` varchar(255) DEFAULT NULL,
  `to_email_address` varchar(255) DEFAULT NULL,
  `transaction_id` varchar(255) DEFAULT NULL,
  `reference_txn_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

CREATE TABLE `user` (
  `ID` int(11) NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `firstname` varchar(64) DEFAULT NULL,
  `lastname` varchar(64) DEFAULT NULL,
  `address` varchar(255) DEFAULT NULL,
  `state` varchar(2) DEFAULT NULL,
  `city` varchar(64) DEFAULT NULL,
  `zip` varchar(5) DEFAULT NULL,
  `phone` varchar(16) DEFAULT NULL,
  `donation_prior_amount` varchar(255) DEFAULT NULL,
  `donation_sum` varchar(255) DEFAULT NULL,
  `donation_time` datetime DEFAULT NULL,
  `uid` int(11) DEFAULT NULL,
  PRIMARY KEY (`ID`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
