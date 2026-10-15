import PageHeader from '../components/PageHeader'
import Placeholder from '../components/Placeholder'
import SubTabs, { PREDICTION_TABS } from '../components/SubTabs'

export default function DwellPredictionPage() {
  return (
    <>
      <PageHeader title="Dwell Time Prediction" subtitle="Prophet vs ARIMA model comparison." />
      <SubTabs tabs={PREDICTION_TABS} />
      <Placeholder text="Dwell prediction is being built." />
    </>
  )
}
