package com.ais140.simulator

import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

/**
 * Configuration for an AIS 140 packet.
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
