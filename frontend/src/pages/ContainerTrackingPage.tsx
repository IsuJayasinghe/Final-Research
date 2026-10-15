import PageHeader from '../components/PageHeader'
import Placeholder from '../components/Placeholder'
import SubTabs, { CONTAINER_TABS } from '../components/SubTabs'

export default function ContainerTrackingPage() {
  return (
    <>
      <PageHeader title="Container Tracking" subtitle="Search, filter, and track all containers in the yard." />
      <SubTabs tabs={CONTAINER_TABS} />
      <Placeholder text="Container tracking is being built." />
    </>
  )
}
