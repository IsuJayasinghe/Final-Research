import PageHeader from '../components/PageHeader'
import Placeholder from '../components/Placeholder'
import SubTabs, { CONTAINER_TABS } from '../components/SubTabs'

export default function ContainerEntryPage() {
  return (
    <>
      <PageHeader title="New Container Arrival" subtitle="Enter container details to get an AI-powered zone recommendation." />
      <SubTabs tabs={CONTAINER_TABS} />
      <Placeholder text="Container entry is being built." />
    </>
  )
}
