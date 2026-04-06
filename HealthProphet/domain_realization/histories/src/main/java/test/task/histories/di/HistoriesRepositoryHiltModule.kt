package test.task.histories.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import test.task.histories.HistoriesRepository
import test.task.histories.HistoriesRepositoryImpl
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HistoriesRepositoryHiltModule {
    @Binds
    @Singleton
    abstract fun bindHistoriesRepository(historiesRepositoryImpl: HistoriesRepositoryImpl): HistoriesRepository
}