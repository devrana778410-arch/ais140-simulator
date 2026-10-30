package com.ais140.simulator

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/**
 * Configuration for an AIS 140 packet across VLTD, CGM, and GPCB profiles.
 */
data class PacketConfig(
    val profile: String = "VLTD",
    val imei: String = "869833088601301",
    val vehicleReg: String = "GJ01AC0000",
    val firmware: String = "4.1.01",
    val vendor: String = "TRAXINA",
    val protocol: String = "NMP",
    val latitude: Double = 21.705100,
    val longitude: Double = 72.995900,
    val altitude: Double = 37.0,
    val speed: Double = 0.0,
    val heading: Double = 247.54,
    val satellites: Int = 27,
    val operator: String = "AIRTEL",
    val mcc: String = "404",
    val mnc: String = "51",
    val cellId: String = "16D5",
    val lac: String = "56C5",
    val hmacKey: String = "26bcb9e368440d4a",
    val seqNum: Int = 1
)

object Ais140Packet {

    private fun getUtcCalendar(): Pair<String, String> {
        val now = Date()
        val dateFmt = SimpleDateFormat("ddMMyyyy", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val timeFmt = SimpleDateFormat("HHmmss", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        return Pair(dateFmt.format(now), timeFmt.format(now))
    }

    private fun formatCoord(value: Double, intDigits: Int = 3): String {
        val absVal = Math.abs(value)
        val intPart = absVal.toInt()
        val fracPart = Math.round((absVal - intPart) * 1_000_000.0).toInt()
        return String.format(Locale.US, "%0${intDigits}d.%06d", intPart, fracPart)
    }

    /**
     * Computes HMAC-SHA256 signature using ASCII key bytes and UTF-8 body bytes.
     */
    private fun hmacSha256(key: String, body: String): String {
        if (key.isBlank()) return ""
        return try {
            val mac = Mac.getInstance("HmacSHA256")
            mac.init(SecretKeySpec(key.toByteArray(Charsets.US_ASCII), "HmacSHA256"))
            mac.doFinal(body.toByteArray(Charsets.UTF_8))
                .joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * Builds standard CGM packet ($NMP wire format with trailing HMAC-SHA256).
     */
    fun buildCgmPacket(config: PacketConfig): String {
        val (dateStr, timeStr) = getUtcCalendar()
        val latStr = formatCoord(config.latitude, 3)
        val lonStr = formatCoord(config.longitude, 3)
        val cellData = "16D5,56C5,56C2,16D5,14,5909,16D5,14,37CB,16D5,14,5980,16D5,14,0000"

        val body = "\$NMP,${config.vendor},4.0.27,NR,01,L,${config.imei},${config.vehicleReg},1," +
                "$dateStr,$timeStr," +
                "$latStr,N,$lonStr,E," +
                String.format(Locale.US, "%.1f", config.speed) + "," +
                String.format(Locale.US, "%.2f", config.heading) + "," +
                "46,136.7,0.7,0.4,${config.operator},0,1,25.8,4.0,0,C,13,404,05," +
                "$cellData,00,001994,0.80,0.00,0,(0,0,0)*"

        val signature = hmacSha256(config.hmacKey, body)
        return "$body,$signature"
    }

    /**
     * Builds standard GPCB packet (Identical to CGM $NMP but WITHOUT trailing HMAC signature).
     */
    fun buildGpcbPacket(config: PacketConfig): String {
        val (dateStr, timeStr) = getUtcCalendar()
        val latStr = formatCoord(config.latitude, 3)
        val lonStr = formatCoord(config.longitude, 3)
        val cellData = "16D5,56C5,56C2,16D5,14,5909,16D5,14,37CB,16D5,14,5980,16D5,14,0000"

        return "\$NMP,${config.vendor},4.0.27,NR,01,L,${config.imei},${config.vehicleReg},1," +
                "$dateStr,$timeStr," +
                "$latStr,N,$lonStr,E," +
                String.format(Locale.US, "%.1f", config.speed) + "," +
                String.format(Locale.US, "%.2f", config.heading) + "," +
                "46,136.7,0.7,0.4,${config.operator},0,1,25.8,4.0,0,C,13,404,05," +
                "$cellData,00,001994,0.80,0.00,0,(0,0,0)*"
    }

    /**
     * Builds PSDN / ONTC GPCB packet format (reverse-engineered from base.apk).
     * Format: $NRM,PSDN,1.ONTC,NR,01,L,<IMEI>,<VEHICLE_NO>,1,...C8CE79AC*
     */
    fun buildPsdnPacket(config: PacketConfig): String {
        val (dateStr, timeStr) = getUtcCalendar()
        val latStr = formatCoord(config.latitude, 3)
        val lonStr = formatCoord(config.longitude, 3)
        val op = if (config.operator.isNotBlank()) config.operator.lowercase(Locale.US) else "airtel"

        return "\$NRM,PSDN,1.ONTC,NR,01,L,${config.imei},${config.vehicleReg},1," +
                "$dateStr,$timeStr," +
                "$latStr,N,$lonStr,E," +
                "0.1,000.00,17,0044.98,1.00,0.59,$op,0,1,26.0,4.0,0,O,16,404,98," +
                "140c,ee1,ed8,140c,11,edd,140c,03,0000,0000,00,0000,0000,00,0000,00," +
                "0.000,0.000,002421,0.140,-,1.0,0,0,23_08_23_1_49._C_1_0_1_75,C8CE79AC*"
    }

    /**
     * Builds standard VLTD $LGN (Login) packet.
     * Format: $LGN,{VREG},{IMEI},{FW},AIS140,{LAT},{LON},*
     */
    fun buildLoginPacket(config: PacketConfig): String {
        val latStr = String.format(Locale.US, "%09.6f", config.latitude)
        val lonStr = String.format(Locale.US, "%09.6f", config.longitude)
        return "\$LGN,${config.vehicleReg},${config.imei},${config.firmware},AIS140,$latStr,$lonStr,*"
    }

    /**
     * Builds standard VLTD $HEL (Health / Diagnostic) packet.
     * Format: $HEL,{VENDOR},{FW},{IMEI},{BATT_PCT},{LOW_BATT},{MEM_ALERT},{IGN_ON_INT},{IGN_OFF_INT},{DI_DO},{SEQ}*
     */
    fun buildHealthPacket(config: PacketConfig): String {
        return "\$HEL,${config.vendor},${config.firmware},${config.imei},100,20,8,10,180,0000,00*"
    }

    /**
     * Builds standard VLTD $PVT periodic tracking packet.
     */
    fun buildPositionPacket(config: PacketConfig): String {
        val (dateStr, timeStr) = getUtcCalendar()
        val seqStr = String.format(Locale.US, "%06d", config.seqNum)
        val latStr = String.format(Locale.US, "%.7f", config.latitude)
        val lonStr = String.format(Locale.US, "%.7f", config.longitude)

        val cellData = "20a8,6359,62b9,20a8,17,635a,20a8,15,6357,20a8,12,621a,20a8,11"

        return "\$PVT,${config.vendor},${config.firmware},NR,1,L,${config.imei},${config.vehicleReg},1," +
                "$dateStr,$timeStr," +
                "$latStr,N,$lonStr,E," +
                String.format(Locale.US, "%05.1f", config.speed) + "," +
                String.format(Locale.US, "%.2f", config.heading) + "," +
                String.format(Locale.US, "%.0f", config.altitude) + "," +
                "20.940,0.75,0.46,${config.operator},0,1,12.5,4.2,0,O,${config.satellites}," +
                "${config.mcc},${config.mnc},$cellData,0001,00,$seqStr,D3*"
    }

    /**
     * Builds VLTD $EPB Emergency Alert (mode = "EMR" or "SEM").
     */
    fun buildEmergencyPacket(config: PacketConfig, mode: String = "EMR"): String {
        val now = Date()
        val dtFmt = SimpleDateFormat("ddMMyyyyHHmmss", Locale.US).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val dtStr = dtFmt.format(now)
        val seqStr = String.format(Locale.US, "%08d", config.seqNum)
        val latStr = String.format(Locale.US, "%.7f", config.latitude)
        val lonStr = String.format(Locale.US, "%.7f", config.longitude)

        return "\$EPB,$mode,${config.imei},NM,$dtStr,A," +
                "$latStr,N,$lonStr,E," +
                "000.0,0.0,000.0,G,${config.vehicleReg},+910000000000,*,$seqStr"
    }
}
