import PageHeader from '../components/PageHeader'
import Placeholder from '../components/Placeholder'
import SubTabs, { PREDICTION_TABS } from '../components/SubTabs'

export default function OccupancyForecastPage() {
  return (
    <>
      <PageHeader title="Yard Occupancy Forecast" subtitle="XGBoost 14-day prediction." />
      <SubTabs tabs={PREDICTION_TABS} />
      <Placeholder text="Occupancy forecast is being built." />
    </>
  )
}
