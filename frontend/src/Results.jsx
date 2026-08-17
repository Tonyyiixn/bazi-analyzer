import { useState, useEffect } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';

// Helper function to colorize Chinese characters based on their Bazi Element
const getElementColor = (char) => {
  const wood = ['甲', '乙', '寅', '卯'];
  const fire = ['丙', '丁', '巳', '午'];
  const earth = ['戊', '己', '辰', '戌', '丑', '未'];
  const metal = ['庚', '辛', '申', '酉'];
  const water = ['壬', '癸', '亥', '子'];

  if (wood.includes(char)) return 'text-el-wood';
  if (fire.includes(char)) return 'text-el-fire';
  if (earth.includes(char)) return 'text-el-earth';
  if (metal.includes(char)) return 'text-el-metal'; // Gold/Metal
  if (water.includes(char)) return 'text-el-water';

  return 'text-parchment-200'; // Default fallback
};

// Maps an English element name (as used in elements/favorable_elements/etc)
// to the same palette as getElementColor, for chips that aren't a single
// Chinese character.
const elementNameColor = (name) => {
  const map = { Wood: 'text-el-wood', Fire: 'text-el-fire', Earth: 'text-el-earth', Metal: 'text-el-metal', Water: 'text-el-water' };
  return map[name] || 'text-parchment-200';
};

const INTERACTION_LABELS = {
  clash: 'Clash', combination: 'Combination', three_harmony: 'Three Harmony',
  punishment: 'Punishment', harm: 'Harm', break: 'Break',
};

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  // Open the backpack to get the data
  const { chartData, formData } = location.state || {};

  // State for the Saving feature
  const [isSaving, setIsSaving] = useState(false);

  // Today's Liu Nian/Liu Yue - fetched live (not part of chartData) since
  // it's a moving fact, not a static property of the natal chart.
  const [currentPeriod, setCurrentPeriod] = useState(null);

  const token = localStorage.getItem('bazi_token');

  useEffect(() => {
    if (!chartData?.pillars) return;
    fetch("http://127.0.0.1:8000/api/v1/current-period", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ pillars: chartData.pillars }),
    })
      .then((res) => res.json())
      .then((data) => { if (data.success) setCurrentPeriod({ liu_nian: data.liu_nian, liu_yue: data.liu_yue }); })
      .catch(() => {});
  }, [chartData?.pillars]);

  // Kick them out if they refresh the page and lose the data
  if (!chartData) {
    return (
      <div className="text-center py-20">
        <p className="text-parchment-400 mb-4">No chart data found!</p>
        <button onClick={() => navigate('/')} className="text-gold-500 font-semibold hover:text-gold-400">Go back to Calculator</button>
      </div>
    );
  }

  // --- THE SAVE FUNCTION ---
  const handleSaveChart = async () => {
    setIsSaving(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/charts/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: formData.name,
          chart_data: chartData,
        }),
      });

      if (!response.ok) throw new Error("Failed to save the chart.");

      alert("Chart saved to your Vault.");
      navigate('/dashboard'); // Auto-redirect them to the vault!

    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-12">
      {/* Back Button */}
      <div className="mb-6">
        <Link to="/" className="text-gold-500 hover:text-gold-400 font-semibold flex items-center gap-2 transition">
          <span>←</span> Calculate Another Chart
        </Link>
      </div>

      <div className="bg-ink-900 border border-ink-700 p-8 rounded mb-8">
        <h2 className="text-xl font-serif-display text-parchment-100 mb-6 text-center">
          Natal Chart for {formData.name}
        </h2>

        {/* 1. The 4 Pillars */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {['Year', 'Month', 'Day', 'Hour'].map((pillar) => {
            const pKey = pillar.toLowerCase();
            return (
              <div key={pillar} className="text-center">
                <p className="text-xs text-parchment-600 uppercase tracking-widest font-semibold mb-2">{pillar}</p>
                <div className="bg-ink-950 border border-ink-700 rounded p-4">
                  {/* Stem (upper) */}
                  <div className="flex flex-col items-center">
                    <span className={`text-3xl font-serif-display ${getElementColor(chartData.pillars[pKey][0])}`}>
                      {chartData.pillars[pKey][0]}
                    </span>
                    <span className="text-xs font-semibold text-gold-500 mt-1">{chartData.ten_gods[pKey].stem}</span>
                  </div>
                  {/* Branch (lower) */}
                  <div className="flex flex-col items-center mt-2 pt-2 border-t border-ink-700">
                    <span className={`text-3xl font-serif-display ${getElementColor(chartData.pillars[pKey][1])}`}>
                      {chartData.pillars[pKey][1]}
                    </span>
                    <span className="text-xs font-semibold text-jade-500 mt-1">{chartData.ten_gods[pKey].branch}</span>
                  </div>
                  {/* Hidden Stems (藏干) - every stem the branch carries, not just main qi */}
                  {chartData.hidden_stems?.[pKey]?.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-ink-700 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1 items-center">
                      {chartData.hidden_stems[pKey].map((hs, i) => (
                        <div key={i} className="contents">
                          <span className={`font-serif-display text-center ${getElementColor(hs.stem)} ${hs.qi_type === 'main' ? 'text-base' : 'text-sm opacity-60'}`}>
                            {hs.stem}
                          </span>
                          <span className={`text-left leading-tight ${hs.qi_type === 'main' ? 'text-[10px] font-semibold text-parchment-300' : 'text-[10px] text-parchment-600'}`}>
                            {hs.ten_god}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* 2. Elemental Progress Bars */}
        <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">Element Strength</h3>
        <div className="grid grid-cols-5 gap-2">
          {Object.entries(chartData.elements).map(([el, val]) => (
            <div key={el} className="text-center">
              <div className="h-24 bg-ink-950 border border-ink-700 rounded relative overflow-hidden flex flex-col justify-end">
                <div
                  className={`w-full transition-all duration-700 ${el === 'Wood' ? 'bg-el-wood' : el === 'Fire' ? 'bg-el-fire' : el === 'Earth' ? 'bg-el-earth' : el === 'Metal' ? 'bg-el-metal' : 'bg-el-water'}`}
                  style={{ height: `${(val / 8) * 100}%` }}
                ></div>
              </div>
              <p className="text-xs font-semibold mt-2 text-parchment-400">{el} ({val})</p>
            </div>
          ))}
        </div>



        {/* 3. The Da Yun (10-Year Luck Pillars) */}
        <div className="pt-6 border-t border-ink-700 mt-6">
            <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">10-Year Luck Pillars (Da Yun)</h3>
            <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
            {chartData.da_yuns.map((yun, index) => (
                <div key={index} className="bg-ink-950 border border-ink-700 rounded p-2 text-center hover:border-gold-500 transition cursor-default">
                <p className="text-xs font-semibold text-parchment-400 mb-1">{yun.start_age}y</p>
                <p className="text-[10px] text-parchment-600 mb-1">{yun.start_year}</p>
                 <div className="flex flex-col items-center text-lg font-serif-display space-y-1 mt-1">
  {String(yun.pillar).split('').map((char, index) => (
    <span key={index} className={getElementColor(char)}>
      {char}
    </span>
  ))}
</div>
            </div>
            ))}
          </div>
        </div>

        {/* 4. Day Master Strength */}
        {chartData.day_master_strength && (
          <div className="pt-6 border-t border-ink-700 mt-6">
            <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">
              Day Master Strength <span className="normal-case font-normal">(via {chartData.day_master_strength.method})</span>
            </h3>
            <div className="flex flex-col items-center gap-3">
              <span className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${
                chartData.day_master_strength.strength === 'strong' ? 'border-el-fire text-el-fire' :
                chartData.day_master_strength.strength === 'weak' ? 'border-el-water text-el-water' :
                'border-parchment-400 text-parchment-400'
              }`}>
                {chartData.day_master_strength.strength.toUpperCase()} ({chartData.day_master_strength.support_weight} support / {chartData.day_master_strength.drain_weight} drain)
              </span>
              {chartData.day_master_strength.favorable_elements.length > 0 && (
                <div className="flex flex-wrap justify-center items-center gap-x-2 gap-y-1 text-xs">
                  <span className="text-parchment-600">Favorable:</span>
                  {chartData.day_master_strength.favorable_elements.map((el) => (
                    <span key={el} className={`font-semibold ${elementNameColor(el)}`}>{el}</span>
                  ))}
                  <span className="text-parchment-600 ml-3">Unfavorable:</span>
                  {chartData.day_master_strength.unfavorable_elements.map((el) => (
                    <span key={el} className="font-semibold text-parchment-600">{el}</span>
                  ))}
                </div>
              )}
              {chartData.day_master_strength.note && (
                <p className="text-xs text-parchment-600 text-center max-w-md italic">{chartData.day_master_strength.note}</p>
              )}
            </div>
          </div>
        )}

        {/* 5. Branch Interactions */}
        {chartData.branch_interactions && (
          <div className="pt-6 border-t border-ink-700 mt-6">
            <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">Branch Interactions</h3>
            {chartData.branch_interactions.length === 0 ? (
              <p className="text-xs text-parchment-600 text-center italic">No active clashes, combinations, or punishments.</p>
            ) : (
              <div className="space-y-2 max-w-md mx-auto">
                {chartData.branch_interactions.map((it, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 bg-ink-950 border border-ink-700 rounded px-3 py-2 text-sm">
                    <span className="text-parchment-200">
                      <span className="text-gold-500 font-semibold">{INTERACTION_LABELS[it.type] || it.type}</span>
                      {it.note ? ` (${it.note})` : ''}: {it.branches.join(' + ')}
                      {it.element ? ` → ${it.element}` : ''}
                    </span>
                    <span className="text-xs text-parchment-600 whitespace-nowrap">{it.positions.join('/')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 6. Stem Combinations */}
        {chartData.stem_combinations && (
          <div className="pt-6 border-t border-ink-700 mt-6">
            <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">Stem Combinations</h3>
            {chartData.stem_combinations.length === 0 ? (
              <p className="text-xs text-parchment-600 text-center italic">No adjacent stem combinations.</p>
            ) : (
              <div className="space-y-1 max-w-md mx-auto">
                {chartData.stem_combinations.map((c, i) => (
                  <div key={i} className="bg-ink-950 border border-ink-700 rounded px-3 py-2 text-sm">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-parchment-200">{c.stems.join(' + ')} → {c.element}</span>
                      <span className="text-xs text-parchment-600 whitespace-nowrap">{c.positions.join('/')}</span>
                    </div>
                    <div className="text-xs text-parchment-600 mt-1">
                      {c.involves_day_master && <span className="text-gold-500 font-semibold mr-2">Day Master</span>}
                      {c.season_supports_transformation ? 'Season supports transformation' : 'Season does not support transformation'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 7. Current Period - Liu Nian & Liu Yue (fetched live, always today) */}
        {currentPeriod && (
          <div className="pt-6 border-t border-ink-700 mt-6">
            <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">
              Current Period — Liu Nian &amp; Liu Yue
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
              <div className="bg-ink-950 border border-ink-700 rounded p-4 text-center">
                <p className="text-xs text-parchment-600 uppercase tracking-widest font-semibold mb-2">
                  Liu Nian ({currentPeriod.liu_nian.year})
                </p>
                <div className="flex justify-center gap-1 mb-2">
                  {String(currentPeriod.liu_nian.pillar).split('').map((char, i) => (
                    <span key={i} className={`text-2xl font-serif-display ${getElementColor(char)}`}>{char}</span>
                  ))}
                </div>
                <p className="text-xs text-gold-500 font-semibold mb-2">
                  {currentPeriod.liu_nian.ten_gods.stem} / {currentPeriod.liu_nian.ten_gods.branch}
                </p>
                {currentPeriod.liu_nian.branch_interactions.length === 0 ? (
                  <p className="text-xs text-parchment-600 italic">No active interactions with the natal chart.</p>
                ) : (
                  <div className="space-y-1 text-left">
                    {currentPeriod.liu_nian.branch_interactions.map((it, i) => (
                      <p key={i} className="text-xs text-parchment-200">
                        <span className="text-gold-500 font-semibold">{INTERACTION_LABELS[it.type] || it.type}</span>
                        {it.note ? ` (${it.note})` : ''}: {it.branches.join(' + ')}{it.element ? ` → ${it.element}` : ''}
                      </p>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-ink-950 border border-ink-700 rounded p-4 text-center">
                <p className="text-xs text-parchment-600 uppercase tracking-widest font-semibold mb-2">
                  Liu Yue ({currentPeriod.liu_yue.year}/{currentPeriod.liu_yue.month})
                </p>
                <div className="flex justify-center gap-1 mb-2">
                  {String(currentPeriod.liu_yue.pillar).split('').map((char, i) => (
                    <span key={i} className={`text-2xl font-serif-display ${getElementColor(char)}`}>{char}</span>
                  ))}
                </div>
                <p className="text-xs text-gold-500 font-semibold mb-2">
                  {currentPeriod.liu_yue.ten_gods.stem} / {currentPeriod.liu_yue.ten_gods.branch}
                </p>
                {currentPeriod.liu_yue.branch_interactions.length === 0 ? (
                  <p className="text-xs text-parchment-600 italic">No active interactions with the natal chart or Liu Nian.</p>
                ) : (
                  <div className="space-y-1 text-left">
                    {currentPeriod.liu_yue.branch_interactions.map((it, i) => (
                      <p key={i} className="text-xs text-parchment-200">
                        <span className="text-gold-500 font-semibold">{INTERACTION_LABELS[it.type] || it.type}</span>
                        {it.note ? ` (${it.note})` : ''}: {it.branches.join(' + ')}{it.element ? ` → ${it.element}` : ''}
                      </p>
                    ))}
                  </div>
                )}
                {currentPeriod.liu_yue.stem_combination_with_day_master && (
                  <p className="text-xs text-jade-400 mt-2">
                    Stem combines with Day Master → {currentPeriod.liu_yue.stem_combination_with_day_master.element}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
    </div>
      {/* ACTION BUTTONS */}
      <div className="flex flex-col sm:flex-row justify-center gap-4 mb-8">
        <button
          onClick={handleSaveChart}
          disabled={isSaving}
          className={`px-8 py-3 rounded font-semibold transition flex items-center justify-center gap-2 ${
            isSaving
              ? 'bg-ink-700 cursor-not-allowed text-parchment-600'
              : 'bg-jade-500 text-ink-950 hover:bg-jade-400'
          }`}
        >
          {isSaving ? 'Saving...' : 'Save Chart to Vault'}
        </button>

        <button
          onClick={() => navigate('/chat', {
            state: {
              chartData: currentPeriod ? { ...chartData, current_period: currentPeriod } : chartData,
              formData,
            },
          })}
          className="px-8 py-3 rounded font-semibold transition flex items-center justify-center gap-2 bg-gold-500 text-ink-950 hover:bg-gold-400"
        >
          Discuss with the Agent
        </button>
      </div>
    </div>
  );
}
