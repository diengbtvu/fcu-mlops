<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Modify predictions table for Hydrogen Production Rate domain.
 * Replaces legacy stimulation parameters with 11 biochemical features.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::table('predictions', function (Blueprint $table) {
            // Drop old legacy columns (if they exist)
            if (Schema::hasColumn('predictions', 'MXene'))       $table->dropColumn('MXene');
            if (Schema::hasColumn('predictions', 'Peptide'))     $table->dropColumn('Peptide');
            if (Schema::hasColumn('predictions', 'Stimulation')) $table->dropColumn('Stimulation');
            if (Schema::hasColumn('predictions', 'Voltage'))     $table->dropColumn('Voltage');
            if (Schema::hasColumn('predictions', 'Result'))      $table->dropColumn('Result');
        });

        Schema::table('predictions', function (Blueprint $table) {
            // 11 input features (Wang et al. 2024)
            $table->float('pH')->comment('System pH value')->after('ml_model_id');
            $table->float('VSS')->comment('Volatile Suspended Solids (mg/L)')->after('pH');
            $table->float('Ethanol')->comment('Average Ethanol concentration (mM)')->after('VSS');
            $table->float('Acetate')->comment('Average Acetic acid concentration (mM)')->after('Ethanol');
            $table->float('Propionate')->comment('Average Propionic acid concentration (mM)')->after('Acetate');
            $table->float('Butyrate')->comment('Total Butyric acid concentration (mM)')->after('Propionate');
            $table->float('Sucrose_Degradation')->comment('TS degradation (%)')->after('Butyrate');
            $table->float('ORP_Mid')->comment('ORP middle position (mV)')->after('Sucrose_Degradation');
            $table->float('ORP_Low')->comment('ORP lower position (mV)')->after('ORP_Mid');
            $table->float('VFA')->comment('Volatile Fatty Acids average (mM)')->after('ORP_Low');
            $table->float('COD_O')->comment('Chemical Oxygen Demand inlet (mg/L)')->after('VFA');

            // Target output: Hydrogen Production Rate
            $table->float('HPR')->comment('Predicted Hydrogen Production Rate (L/h/L)')->after('COD_O');
        });
    }

    public function down(): void
    {
        Schema::table('predictions', function (Blueprint $table) {
            $table->dropColumn([
                'pH', 'VSS', 'Ethanol', 'Acetate', 'Propionate',
                'Butyrate', 'Sucrose_Degradation', 'ORP_Mid', 'ORP_Low',
                'VFA', 'COD_O', 'HPR',
            ]);
        });

        Schema::table('predictions', function (Blueprint $table) {
            $table->float('MXene')->after('ml_model_id');
            $table->float('Peptide')->after('MXene');
            $table->float('Stimulation')->after('Peptide');
            $table->float('Voltage')->after('Stimulation');
            $table->float('Result')->after('Voltage');
        });
    }
};
